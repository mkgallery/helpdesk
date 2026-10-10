from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render

import csv

from django.http import HttpResponse

from .forms import CommentForm, TicketForm, TrackForm, phone_key
from .models import Ticket, TicketAttachment, User
from .reports import all_offices, all_staff, filtered_tickets
from .sms import (
    notify_ticket_assigned,
    notify_ticket_comment,
    notify_ticket_status,
)


MAX_FILES = 5
MAX_FILE_MB = 10


def role_required(*roles):
    def decorator(view):
        @wraps(view)
        def wrapper(request, *args, **kwargs):
            if request.user.role not in roles:
                raise PermissionDenied
            return view(request, *args, **kwargs)
        return login_required(wrapper)
    return decorator


# ---------- Public: employees (no login) ----------
def ticket_create(request):
    form = TicketForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        files = request.FILES.getlist("attachments")
        if len(files) > MAX_FILES or any(f.size > MAX_FILE_MB * 1024 * 1024 for f in files):
            form.add_error(None, f"Attach at most {MAX_FILES} files of {MAX_FILE_MB} MB each.")
        else:
            ticket = form.save()
            for f in files:
                TicketAttachment.objects.create(ticket=ticket, file=f)
            request.session["last_ticket_id"] = ticket.pk
            return redirect("ticket_submitted")
    return render(request, "tickets/ticket_form.html", {"form": form})


def ticket_submitted(request):
    ticket = Ticket.objects.filter(pk=request.session.get("last_ticket_id")).first()
    if ticket is None:
        return redirect("ticket_create")
    return render(request, "tickets/ticket_submitted.html", {"ticket": ticket})


def ticket_track(request):
    form = TrackForm(request.POST or None)
    ticket = None
    searched = False
    stages = []
    if request.method == "POST" and form.is_valid():
        searched = True
        # Closed tickets have no number, so only active tickets can be found.
        ticket = (
            Ticket.objects.filter(
                number=form.cleaned_data["number"],
                requester_phone__endswith=phone_key(form.cleaned_data["phone"]),
            )
            .select_related("assigned_to")
            .first()
        )
        if ticket:
            order = [value for value, _ in Ticket.Status.choices]
            labels = dict(Ticket.Status.choices)
            current = order.index(ticket.status)
            stages = [
                {
                    "label": labels[value],
                    "state": "done" if i < current else "current" if i == current else "todo",
                }
                for i, value in enumerate(order)
            ]
    return render(request, "tickets/ticket_track.html", {
        "form": form,
        "ticket": ticket,
        "searched": searched,
        "stages": stages,
    })


# ---------- IT staff + supervisor (login required) ----------
@login_required
def dashboard(request):
    if request.user.is_supervisor:
        return redirect("supervisor_dashboard")
    return redirect("ticket_list")


@role_required(User.Role.STAFF, User.Role.SUPERVISOR)
def ticket_list(request):
    tickets = Ticket.objects.select_related("assigned_to")
    status = request.GET.get("status")
    if status in dict(Ticket.Status.choices):
        tickets = tickets.filter(status=status)
    else:
        # closed tickets leave the active list (they stay under the Closed filter)
        tickets = tickets.exclude(status=Ticket.Status.CLOSED)

    # --- IT Staff see ONLY unassigned tickets OR tickets assigned to them.
    # Supervisors still see everything.
    if request.user.role == User.Role.STAFF:
        tickets = tickets.filter(
            Q(assigned_to__isnull=True) | Q(assigned_to=request.user)
        )
    # -----------------------------------------------------------------------

    flt = request.GET.get("filter")
    if flt == "mine":
        tickets = tickets.filter(assigned_to=request.user)
    elif flt == "unassigned":
        tickets = tickets.filter(assigned_to__isnull=True)

    return render(request, "tickets/ticket_list.html", {
        "tickets": tickets,
        "title": "Tickets",
        "show_filters": True,
        "statuses": Ticket.Status.choices,
    })


@role_required(User.Role.SUPERVISOR)
def supervisor_dashboard(request):
    counts = {s: Ticket.objects.filter(status=s).count() for s, _ in Ticket.Status.choices}
    unassigned = Ticket.objects.filter(assigned_to__isnull=True).exclude(
        status__in=[Ticket.Status.RESOLVED, Ticket.Status.CLOSED]
    ).count()
    active = ~Q(assigned_tickets__status__in=[Ticket.Status.RESOLVED, Ticket.Status.CLOSED])
    staff = User.objects.filter(role=User.Role.STAFF).annotate(
        active_count=Count("assigned_tickets", filter=active),
        total_count=Count("assigned_tickets"),
    )
    return render(request, "tickets/supervisor_dashboard.html", {
        "counts": counts,
        "total": Ticket.objects.count(),
        "unassigned": unassigned,
        "staff": staff,
        "recent": Ticket.objects.select_related("assigned_to")[:8],
    })


@role_required(User.Role.STAFF, User.Role.SUPERVISOR)
def ticket_detail(request, pk):
    ticket = get_object_or_404(Ticket, pk=pk)
    user = request.user
    can_work = user.is_supervisor or ticket.assigned_to_id in (None, user.id)

    if request.method == "POST":
        action = request.POST.get("action")
        if action == "comment":
            form = CommentForm(request.POST)
            if form.is_valid():
                c = form.save(commit=False)
                c.ticket, c.author = ticket, user
                c.save()
                # --- SMS: notify requester of the new reply ---
                notify_ticket_comment(ticket, c)

        elif action == "take" and can_work:
            ticket.assigned_to = user
            if ticket.status == Ticket.Status.OPEN:
                ticket.status = Ticket.Status.IN_PROGRESS
            ticket.save()
            # --- SMS: notify requester their ticket is being handled ---
            notify_ticket_assigned(ticket, user)
            messages.success(request, "You are now handling this ticket.")

        elif action == "status" and can_work:
            new_status = request.POST.get("status")
            if new_status in dict(Ticket.Status.choices):
                ticket.status = new_status
                ticket.save()
                # --- SMS: notify requester of the status change ---
                notify_ticket_status(ticket)
                if new_status == Ticket.Status.CLOSED:
                    messages.success(request, "Ticket closed. Its number is free for a new ticket.")
                else:
                    messages.success(request, "Status updated.")

        elif action == "assign" and user.is_supervisor:
            staff_user = User.objects.filter(
                pk=request.POST.get("assigned_to"), role=User.Role.STAFF
            ).first()
            if staff_user:
                ticket.assigned_to = staff_user
                if ticket.status == Ticket.Status.OPEN:
                    ticket.status = Ticket.Status.IN_PROGRESS
                ticket.save()
                # --- SMS: notify requester who is handling the ticket ---
                notify_ticket_assigned(ticket, staff_user)
                messages.success(request, f"Assigned to {staff_user.username}.")

        # ---------------- NEW: internal handoff between IT staff ----------------
        # Only the currently assigned staff member can hand off.
        # No SMS to the employee — this is an internal change of hands.
        elif action == "handoff" and ticket.assigned_to_id == user.id:
            new_staff = User.objects.filter(
                pk=request.POST.get("new_staff"),
                role=User.Role.STAFF,
            ).exclude(pk=user.id).first()
            if new_staff:
                ticket.assigned_to = new_staff
                ticket.save()
                messages.success(request, f"Ticket handed off to {new_staff.username}.")
            else:
                messages.error(request, "Please choose a valid staff member.")
        # ------------------------------------------------------------------------

        else:
            raise PermissionDenied
        return redirect("ticket_detail", pk=ticket.pk)

    # For the handoff dropdown — all IT staff except the current user
    other_staff = User.objects.filter(role=User.Role.STAFF).exclude(pk=user.pk)

    return render(request, "tickets/ticket_detail.html", {
        "ticket": ticket,
        "comment_form": CommentForm(),
        "can_work": can_work,
        "statuses": Ticket.Status.choices,
        "staff_members": User.objects.filter(role=User.Role.STAFF) if user.is_supervisor else None,
        "other_staff": other_staff,
    })
# ---------- Reports (supervisor only) ----------
@role_required(User.Role.SUPERVISOR)
def reports(request):
    tickets = filtered_tickets(request.GET)
    return render(request, "tickets/reports.html", {
        "tickets": tickets,
        "ticket_count": tickets.count(),
        "offices": all_offices(),
        "staff_list": all_staff(),
        "statuses": Ticket.Status.choices,
        "priorities": Ticket.Priority.choices,
        "params": request.GET,     # so the template can re-fill the form
    })


@role_required(User.Role.SUPERVISOR)
def reports_csv(request):
    """Download the current filtered report as CSV."""
    tickets = filtered_tickets(request.GET)

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="tickets_report.csv"'

    writer = csv.writer(response)
    writer.writerow([
        "Ticket #", "Title", "Status", "Priority", "Office",
        "Requester name", "Requester phone",
        "Assigned to",
        "Created at", "Updated at", "Resolved at",
    ])

    for t in tickets:
        writer.writerow([
            t.number if t.number is not None else t.closed_number or t.pk,
            t.title,
            t.get_status_display(),
            t.get_priority_display(),
            t.office,
            t.requester_name,
            t.requester_phone,
            t.assigned_to.username if t.assigned_to else "",
            t.created_at.strftime("%Y-%m-%d %H:%M") if t.created_at else "",
            t.updated_at.strftime("%Y-%m-%d %H:%M") if t.updated_at else "",
            t.closed_at.strftime("%Y-%m-%d %H:%M") if t.closed_at else "",
        ])

    return response