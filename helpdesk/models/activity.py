"""Ticket conversations, attachment records, and private file destinations."""
from pathlib import Path
from uuid import uuid4

from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.db import models
from django.utils import timezone


def private_storage():
    return FileSystemStorage(location=settings.HELPDESK_UPLOAD_ROOT)


def attachment_path(instance, filename):
    return f'{instance.ticket_id}/{uuid4().hex}{Path(filename).suffix.lower()}'


class TicketComment(models.Model):
    ticket = models.ForeignKey('helpdesk.Ticket', on_delete=models.PROTECT, related_name='comments')
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    body = models.TextField(max_length=10000, blank=True)
    internal = models.BooleanField(default=False, help_text='Internal notes are visible only to authorized IT staff.')
    created_at = models.DateTimeField(default=timezone.now, editable=False)

    class Meta:
        ordering = ['created_at', 'pk']

    def __str__(self):
        return f'{self.ticket.number} — {self.author}'


class TicketAttachment(models.Model):
    ticket = models.ForeignKey('helpdesk.Ticket', on_delete=models.PROTECT, related_name='attachments')
    comment = models.ForeignKey(TicketComment, on_delete=models.PROTECT, null=True, blank=True, related_name='attachments')
    uploader = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    file = models.FileField(storage=private_storage, upload_to=attachment_path, max_length=255)
    original_name = models.CharField(max_length=255)
    size = models.PositiveIntegerField()
    created_at = models.DateTimeField(default=timezone.now, editable=False)

    def __str__(self):
        return self.original_name
