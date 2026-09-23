"""Submitted tickets, original request snapshots, and status lifecycle rules."""
from django.conf import settings
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models
from django.utils import timezone

MAX_TEXT_LENGTH = 10000

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

    class Dept(models.TextChoices):
        BLANK = '' , ''
        ACCT_MGT = 'account_mgt', 'Account Management'
        CALIBRATE = 'calibrate', 'Calibrate'
        CLEAN_ROOM = 'clean_room', 'Clean Room'
        CUST_SERVICE = 'customer_service', 'Customer Service'
        DATA_CENTER = 'data_center', 'Data Center'
        GENERAL = 'general', 'General'
        GENERAL_IT ='general_it', 'General IT'
        INDUCT = 'inductions', 'Inductions'
        MARINE = 'marine', 'Marine'
        MARKETING = 'marketing', 'Marketing'
        QA = 'qa', 'QA'
        SALES = 'sales', 'Sales'
        SHIPPING = 'shipping', 'Shipping And Receiving'

    OPEN_STATUSES = (Status.NEW, Status.IN_PROGRESS, Status.WAITING)
    category = models.ForeignKey('helpdesk.Category', on_delete=models.PROTECT)
    ticket_type = models.ForeignKey('helpdesk.TicketType', on_delete=models.PROTECT)

    requester = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='requested_tickets')
    dept = models.CharField(max_length=20, choices=Dept.choices, default=Dept.BLANK)
    assignee = models.ForeignKey(settings.AUTH_USER_MODEL,
                                 on_delete=models.SET_NULL,
                                 null=True,
                                 blank=True,
                                 related_name='assigned_tickets')

    subject = models.CharField(max_length=200)
    description = models.TextField(max_length = MAX_TEXT_LENGTH)
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
