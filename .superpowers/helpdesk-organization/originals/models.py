from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.storage import FileSystemStorage
from django.core.serializers.json import DjangoJSONEncoder
from django.utils import timezone
from pathlib import Path
from uuid import uuid4


def private_storage():
    return FileSystemStorage(location=settings.HELPDESK_UPLOAD_ROOT)


def attachment_path(instance, filename):
    return f'{instance.ticket_id}/{uuid4().hex}{Path(filename).suffix.lower()}'


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.CharField(max_length=250, blank=True)
    position = models.PositiveIntegerField(default=0)
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ['position', 'name']
        verbose_name_plural = 'categories'

    def __str__(self):
        return self.name


class TicketType(models.Model):
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name='ticket_types')
    name = models.CharField(max_length=100)
    description = models.CharField(max_length=250, blank=True)
    position = models.PositiveIntegerField(default=0)
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ['position', 'name']
        constraints = [models.UniqueConstraint(fields=['category', 'name'], name='helpdesk_unique_type')]

    def __str__(self):
        return self.name


class TicketField(models.Model):
    class Kind(models.TextChoices):
        TEXT = 'text', 'Short text'
        TEXTAREA = 'textarea', 'Long text'
        EMAIL = 'email', 'Email'
        INTEGER = 'integer', 'Whole number'
        DECIMAL = 'decimal', 'Decimal number'
        DATE = 'date', 'Date'
        CHECKBOX = 'checkbox', 'Checkbox (required means checked)'
        DROPDOWN = 'dropdown', 'Dropdown'
        MULTIPLE = 'multiple_choice', 'Multiple choice'

    ticket_type = models.ForeignKey(TicketType, on_delete=models.CASCADE, related_name='fields')
    label = models.CharField(max_length=120)
    field_type = models.CharField(max_length=24, choices=Kind.choices, default=Kind.TEXT)
    required = models.BooleanField(default=False)
    help_text = models.CharField(max_length=300, blank=True)
    choices = models.TextField(blank=True, help_text='Dropdown/multiple choice only: one unique option per line (maximum 100).')
    position = models.PositiveIntegerField(default=0)
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ['position', 'pk']

    @property
    def options(self):
        return [line.strip() for line in self.choices.splitlines() if line.strip()]

    def clean(self):
        super().clean()
        if not self.label.strip():
            raise ValidationError({'label': 'Enter a field label.'})
        if self.field_type in (self.Kind.DROPDOWN, self.Kind.MULTIPLE):
            options = self.options
            if not options or len(options) > 100 or len(options) != len(set(options)) or any(len(x) > 200 for x in options):
                raise ValidationError({'choices': 'Enter 1–100 unique options, up to 200 characters each.'})

    def __str__(self):
        return self.label


class Ticket(models.Model):
    class Status(models.TextChoices):
        NEW = 'new', 'New'
        IN_PROGRESS = 'in_progress', 'In progress'
        WAITING = 'waiting', 'Waiting'
        RESOLVED = 'resolved', 'Resolved'
        CLOSED = 'closed', 'Closed'

    class Priority(models.TextChoices):
        LOW = 'low', 'Low'
        NORMAL = 'normal', 'Normal'
        HIGH = 'high', 'High'
        URGENT = 'urgent', 'Urgent'

    OPEN_STATUSES = (Status.NEW, Status.IN_PROGRESS, Status.WAITING)
    category = models.ForeignKey(Category, on_delete=models.PROTECT)
    ticket_type = models.ForeignKey(TicketType, on_delete=models.PROTECT)
    requester = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='requested_tickets')
    assignee = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_tickets')
    subject = models.CharField(max_length=200)
    description = models.TextField(max_length=10000)
    priority = models.CharField(max_length=12, choices=Priority.choices, default=Priority.NORMAL)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.NEW, db_index=True)
    answers = models.JSONField(default=list, encoder=DjangoJSONEncoder, blank=True)
    category_label = models.CharField(max_length=100, blank=True)
    type_label = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(default=timezone.now, editable=False, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    resolved_at = models.DateTimeField(null=True, blank=True, editable=False)
    closed_at = models.DateTimeField(null=True, blank=True, editable=False)

    class Meta:
        ordering = ['-created_at', '-pk']
        permissions = [('view_reports', 'Can view helpdesk reports')]

    @property
    def number(self):
        return f'IT-{self.pk:05d}'

    def save(self, *args, **kwargs):
        if not self.pk:
            self.category_label = self.category.name
            self.type_label = self.ticket_type.name
        if self.status == self.Status.RESOLVED and not self.resolved_at:
            self.resolved_at = timezone.now()
        if self.status == self.Status.CLOSED and not self.closed_at:
            self.closed_at = timezone.now()
        if self.status in self.OPEN_STATUSES:
            self.resolved_at = self.closed_at = None
        elif self.status == self.Status.RESOLVED:
            self.closed_at = None
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.number} · {self.subject}'


class TicketComment(models.Model):
    ticket = models.ForeignKey(Ticket, on_delete=models.PROTECT, related_name='comments')
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    body = models.TextField(max_length=10000, blank=True)
    internal = models.BooleanField(default=False, help_text='Internal notes are visible only to authorized IT staff.')
    created_at = models.DateTimeField(default=timezone.now, editable=False)

    class Meta:
        ordering = ['created_at', 'pk']

    def __str__(self):
        return f'{self.ticket.number} — {self.author}'


class TicketAttachment(models.Model):
    ticket = models.ForeignKey(Ticket, on_delete=models.PROTECT, related_name='attachments')
    comment = models.ForeignKey(TicketComment, on_delete=models.PROTECT, null=True, blank=True, related_name='attachments')
    uploader = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    file = models.FileField(storage=private_storage, upload_to=attachment_path, max_length=255)
    original_name = models.CharField(max_length=255)
    size = models.PositiveIntegerField()
    created_at = models.DateTimeField(default=timezone.now, editable=False)

    def __str__(self):
        return self.original_name
