# tickets/sms.py
"""
SMS utility for Meseji (https://meseji.co.tz).

Confirmed working configuration:
    Endpoint:  POST https://meseji.co.tz/api/v1/sms/send
    Auth:      x-api-key: <MESEJI_TOKEN>
    Body:      {"sender_id": "MESEJI", "contacts": "2557XXXXXXXX", "message": "..."}
    Response:  {"status":"success","batch_id":"...","new_balance":...}
"""

import logging
import requests
from django.conf import settings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Phone number normalisation
# ---------------------------------------------------------------------------
def normalize_phone(raw):
    """
    Convert a phone number to Meseji's expected format: 255XXXXXXXXX (no '+').
    Examples:
        0712345678    -> 255712345678
        +255712345678 -> 255712345678
        255712345678  -> 255712345678
        712345678     -> 255712345678
    Returns None if we can't make sense of it.
    """
    if not raw:
        return None

    digits = "".join(c for c in str(raw) if c.isdigit())
    if not digits:
        return None

    if digits.startswith("255"):
        return digits
    if digits.startswith("0"):
        return "255" + digits[1:]
    if len(digits) == 9:
        return "255" + digits
    return digits


# ---------------------------------------------------------------------------
# The send function
# ---------------------------------------------------------------------------
def send_sms(phone_number, message):
    """
    Send an SMS via Meseji. Returns True on success, False otherwise.
    Never raises — SMS failures must never break the ticket workflow.
    """
    if not getattr(settings, "SMS_ENABLED", True):
        logger.info("SMS disabled — skipping send to %s", phone_number)
        return False

    token = getattr(settings, "MESEJI_TOKEN", "")
    base_url = getattr(settings, "MESEJI_BASE_URL", "https://meseji.co.tz/api/v1")
    sender_id = getattr(settings, "MESEJI_SENDER_ID", "MESEJI")

    if not token:
        logger.warning("MESEJI_TOKEN not set — cannot send SMS")
        return False

    phone = normalize_phone(phone_number)
    if not phone:
        logger.warning("Invalid phone number: %r", phone_number)
        return False

    url = f"{base_url.rstrip('/')}/sms/send"

    headers = {
        "x-api-key": token,
        "Accept": "application/json",
        "Content-Type": "application/json",
    }

    body = {
        "sender_id": sender_id,
        "contacts": phone,          # NOTE: string, not list — Meseji requires this
        "message": message,
    }

    try:
        resp = requests.post(url, json=body, headers=headers, timeout=15)
    except requests.RequestException as e:
        logger.error("SMS request exception to %s: %s", phone, e)
        return False

    if 200 <= resp.status_code < 300:
        logger.info("SMS sent OK to %s — %s", phone, resp.text[:200])
        return True

    logger.error(
        "SMS failed (%d) to %s — %s",
        resp.status_code, phone, resp.text[:300],
    )
    return False


# ---------------------------------------------------------------------------
# High-level notification helpers (called from views)
# ---------------------------------------------------------------------------

def notify_ticket_comment(ticket, comment):
    """SMS the requester when IT staff posts a reply on their ticket."""
    if not ticket.requester_phone:
        return False
    author_name = comment.author.get_full_name() or comment.author.username
    msg = (
        f"Helpdesk {ticket.display_number}: new reply from {author_name}. "
        f"{comment.message[:120]}"
    )
    return send_sms(ticket.requester_phone, msg)


def notify_ticket_status(ticket):
    """SMS the requester when the ticket status changes."""
    if not ticket.requester_phone:
        return False
    status_label = ticket.get_status_display()
    msg = f"Helpdesk {ticket.display_number}: status is now {status_label}."
    return send_sms(ticket.requester_phone, msg)


def notify_ticket_assigned(ticket, staff_user):
    """SMS the requester when their ticket is assigned to a staff member."""
    if not ticket.requester_phone:
        return False
    name = staff_user.get_full_name() or staff_user.username
    msg = f"Helpdesk {ticket.display_number}: {name} is now handling your ticket."
    return send_sms(ticket.requester_phone, msg)