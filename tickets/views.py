from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render

from .forms import CommentForm, TicketForm
from .models import Ticket, TicketAttachment, User

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
    flt = request.GET.get("filter")
    if flt == "mine":
        tickets = tickets.filter(assigned_to=request.user)
    elif flt == "unassigned":
        tickets = tickets.filter(assigned_to__isnull=True)
    return render(request, "tickets/ticket_list.html", {
        "tickets": tickets,
        "title": "All tickets",
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
        elif action == "take" and can_work:
            ticket.assigned_to = user
            if ticket.status == Ticket.Status.OPEN:
                ticket.status = Ticket.Status.IN_PROGRESS
            ticket.save()
            messages.success(request, "You are now handling this ticket.")
        elif action == "status" and can_work:
            new_status = request.POST.get("status")
            if new_status in dict(Ticket.Status.choices):
                ticket.status = new_status
                ticket.save()
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
                messages.success(request, f"Assigned to {staff_user.username}.")
        else:
            raise PermissionDenied
        return redirect("ticket_detail", pk=ticket.pk)

    return render(request, "tickets/ticket_detail.html", {
        "ticket": ticket,
        "comment_form": CommentForm(),
        "can_work": can_work,
        "statuses": Ticket.Status.choices,
        "staff_members": User.objects.filter(role=User.Role.STAFF) if user.is_supervisor else None,
    })