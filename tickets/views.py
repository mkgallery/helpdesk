from functools import wraps

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render

from .forms import CommentForm, RegisterForm, TicketForm
from .models import Ticket, TicketAttachment, User


def role_required(*roles):
    def decorator(view):
        @wraps(view)
        def wrapper(request, *args, **kwargs):
            if request.user.role not in roles:
                raise PermissionDenied
            return view(request, *args, **kwargs)
        return login_required(wrapper)
    return decorator


def register(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    form = RegisterForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()  # always created as an employee
        login(request, user)
        return redirect("dashboard")
    return render(request, "registration/register.html", {"form": form})


@login_required
def dashboard(request):
    if request.user.is_supervisor:
        return redirect("supervisor_dashboard")
    if request.user.is_staff_member:
        return redirect("ticket_list")
    return redirect("my_tickets")


# ---------- Employee ----------
@role_required(User.Role.EMPLOYEE)
def ticket_create(request):
    form = TicketForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        ticket = form.save(commit=False)
        ticket.created_by = request.user
        ticket.save()
        for f in request.FILES.getlist("attachments"):
            TicketAttachment.objects.create(ticket=ticket, file=f)
        messages.success(request, f"Ticket #{ticket.pk} created. IT staff can now see it.")
        return redirect("ticket_detail", pk=ticket.pk)
    return render(request, "tickets/ticket_form.html", {"form": form})


@role_required(User.Role.EMPLOYEE)
def my_tickets(request):
    tickets = Ticket.objects.filter(created_by=request.user).select_related("assigned_to")
    return render(request, "tickets/ticket_list.html", {"tickets": tickets, "title": "My tickets"})


# ---------- IT staff + supervisor ----------
@role_required(User.Role.STAFF, User.Role.SUPERVISOR)
def ticket_list(request):
    tickets = Ticket.objects.select_related("created_by", "assigned_to")
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
        "recent": Ticket.objects.select_related("created_by", "assigned_to")[:8],
    })


# ---------- Shared detail page ----------
@login_required
def ticket_detail(request, pk):
    ticket = get_object_or_404(Ticket, pk=pk)
    user = request.user
    if user.is_employee and ticket.created_by_id != user.id:
        raise PermissionDenied

    can_work = user.is_supervisor or (
        user.is_staff_member and ticket.assigned_to_id in (None, user.id)
    )

    if request.method == "POST":
        action = request.POST.get("action")
        if action == "comment":
            form = CommentForm(request.POST)
            if form.is_valid():
                c = form.save(commit=False)
                c.ticket, c.author = ticket, user
                c.save()
        elif action == "take" and can_work and not user.is_employee:
            ticket.assigned_to = user
            if ticket.status == Ticket.Status.OPEN:
                ticket.status = Ticket.Status.IN_PROGRESS
            ticket.save()
            messages.success(request, "You are now handling this ticket.")
        elif action == "status" and can_work and not user.is_employee:
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
