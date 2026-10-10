# tickets/reports.py
"""
Shared filtering logic for reports — used by both the HTML report
view and the CSV download view, so they always return the same data.
"""

from datetime import date, datetime, timedelta

from django.db.models import Q
from django.utils import timezone

from .models import Ticket, User


# Allowed date-range presets (label, value)
DATE_PRESETS = [
    ("all",        "All time"),
    ("today",      "Today"),
    ("this_week",  "This week"),
    ("this_month", "This month"),
    ("this_year",  "This year"),
    ("custom",     "Custom range"),
]


def _parse_date(s):
    """Turn 'YYYY-MM-DD' into a date, or return None if invalid."""
    if not s:
        return None
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def resolve_date_range(params):
    """
    Return (start_date, end_date) as date objects (or None for 'no bound')
    based on ?range= and ?from= / ?to= query params.
    """
    preset = params.get("range", "all")
    today = timezone.localdate()

    if preset == "today":
        return today, today
    if preset == "this_week":
        start = today - timedelta(days=today.weekday())  # Monday
        return start, today
    if preset == "this_month":
        return today.replace(day=1), today
    if preset == "this_year":
        return today.replace(month=1, day=1), today
    if preset == "custom":
        return _parse_date(params.get("from")), _parse_date(params.get("to"))

    # "all" or anything else
    return None, None


def filtered_tickets(params):
    """
    Apply every supported filter from the query string and return
    a QuerySet of Ticket objects, ordered newest first.
    """
    qs = Ticket.objects.select_related("assigned_to")

    # ---- date range ----
    start, end = resolve_date_range(params)
    if start:
        qs = qs.filter(created_at__date__gte=start)
    if end:
        qs = qs.filter(created_at__date__lte=end)

    # ---- status ----
    status = params.get("status", "")
    if status in dict(Ticket.Status.choices):
        qs = qs.filter(status=status)

    # ---- priority ----
    priority = params.get("priority", "")
    if priority in dict(Ticket.Priority.choices):
        qs = qs.filter(priority=priority)

    # ---- office ----
    office = params.get("office", "").strip()
    if office:
        qs = qs.filter(office__icontains=office)

    # ---- assigned staff ----
    assigned = params.get("assigned_to", "")
    if assigned == "unassigned":
        qs = qs.filter(assigned_to__isnull=True)
    elif assigned.isdigit():
        qs = qs.filter(assigned_to_id=int(assigned))

    # ---- text search (ticket number, title, requester) ----
    q = params.get("q", "").strip()
    if q:
        cond = (
            Q(title__icontains=q)
            | Q(requester_name__icontains=q)
            | Q(requester_phone__icontains=q)
        )
        if q.isdigit():
            cond |= Q(number=int(q)) | Q(closed_number=int(q))
        qs = qs.filter(cond)

    return qs.order_by("-created_at")


def all_offices():
    """Distinct list of office values for the filter dropdown."""
    return (
        Ticket.objects.exclude(office="")
        .values_list("office", flat=True)
        .distinct()
        .order_by("office")
    )


def all_staff():
    """IT staff for the assigned-to filter dropdown."""
    return User.objects.filter(role=User.Role.STAFF).order_by("username")