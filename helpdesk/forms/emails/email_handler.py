"""Email notifications for newly submitted helpdesk tickets."""
import logging

from django.conf import settings
from django.core.mail import EmailMessage
from django.core.validators import validate_email
from django.utils import timezone

from .message_factory import generate_msg_from_Form
from ...models import Ticket

logger = logging.getLogger(__name__)


def send_ticket_created_emails(ticket_id: int, ticket_url: str) -> int:
    """Attempt both notifications; return the number the backend accepted."""

    ticket = Ticket.objects.select_related("requester").get(pk=ticket_id)
    support_email = settings.HELPDESK_NOTIFICATIONS_EMAIL.strip()

    validate_email(ticket.requester_email)
    validate_email(support_email)

    # Ticket subjects come from user input; keep the email header single-line.
    subject = f"[Ticket:{ticket.number}] {' '.join(ticket.subject.splitlines())}"

    body = generate_msg_from_Form(
        ticket,
        ticket_url, )

    sent_count = 0

    try:
        sent = EmailMessage(
            subject=subject,
            body=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to= [ticket.requester_email],
            cc = [support_email],
            reply_to=[support_email],
        ).send()

        sent_count += sent or 0

    except Exception:
        logger.exception(
            "Failed %s email for %s",
            ticket.number,
        )
        logger.error(
                "No %s email sent for %s",
                ticket.number,
                )

    return sent_count

def urgency_notification(ticket_id, ticket_url, manager_email):
    """
    If urgency set to high or urgent, notifiy manager
    """
    ticket = Ticket.objects.select_related("requester").get(pk = ticket_id)
    support_email = settings.HELPDESK_NOTIFICATIONS_EMAIL.strip()

    validate_email(support_email)
    validate_email(manager_email)

    # Ticket subjects come from user input; keep the email header single-line.
    subject = f"[High Priority Ticket:{ticket.number}] {' '.join(ticket.subject.splitlines())}"

    body = generate_msg_from_Form(
            ticket,
            ticket_url,
            high_priority = True)

    sent_count = 0

    try :
        sent = EmailMessage(
                subject = subject,
                body = body,
                from_email = settings.DEFAULT_FROM_EMAIL,
                to = [manager_email],
                cc = [support_email],
                reply_to = [support_email],
                ).send()

        sent_count += sent or 0

    except Exception :
        logger.exception(
                "Failed %s email for %s",
                ticket.number,
                )
        logger.error(
                "No %s email sent for %s",
                ticket.number,
                )

    return sent_count