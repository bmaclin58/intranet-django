"""Categories, request types, and configurable fields used to build ticket forms."""
from django.core.exceptions import ValidationError
from django.db import models
import os
from django.conf import settings

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
        constraints = [models.UniqueConstraint(fields=['category', 'name'],
                                               name='helpdesk_unique_type')]

    def __str__(self):
        return self.name


class TicketField(models.Model):
    class Kind(models.TextChoices):
        TEXT = 'text', 'Short text'
        TEXTAREA = 'textarea', 'Long text'
        EMAIL = 'email', 'Email'
        PHONE = 'phone', 'Phone'
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

def Software_file_path():
    return os.path.join(settings.LOCAL_FILE_DIR, "software")


class ApprovedSoftware(models.Model) :
    software_Name = models.CharField(max_length = 150)
    download_site = models.URLField(name = 'Download Website', blank = True, null = True)
    file_location = models.FilePathField(path = Software_file_path,
                                         allow_folders = True,
                                         name = 'File / Folder Path',
                                         blank = True, null = True)

    class Meta:
        ordering = ['software_Name']
        verbose_name_plural = 'Approved Software Files'