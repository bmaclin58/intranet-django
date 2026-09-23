from django.db import transaction
from django.utils import timezone

from .models import Ticket
from .uploads import cleanup_attachments, save_attachments


def save_ticket_activity(ticket, user, files, comment=None):
    written = []
    try:
        with transaction.atomic():
            if ticket.pk:
                # Replies must not overwrite an assignment/status changed after this ticket was read.
                Ticket.objects.filter(pk=ticket.pk).update(updated_at=timezone.now())
            else:
                ticket.save()
            if comment is not None:
                comment.save()
            save_attachments(ticket, user, files, written, comment)
    except Exception:
        cleanup_attachments(written)
        raise
