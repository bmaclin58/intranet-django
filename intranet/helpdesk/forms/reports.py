"""Validate staff report filters, including inclusive creation-date ranges."""
from django import forms as django_forms
from django.core.exceptions import ValidationError

from ..models import Category, Ticket


class ReportFilters(django_forms.Form):
    created_from = django_forms.DateField(required=False,
                                          widget=django_forms.DateInput(attrs={'type': 'date'}))
    created_to = django_forms.DateField(required=False,
                                        widget=django_forms.DateInput(attrs={'type': 'date'}))
    category = django_forms.ModelChoiceField(queryset=Category.objects.all(), required=False,
                                             empty_label='All categories')
    status = django_forms.ChoiceField(choices=[('', 'All statuses'), *Ticket.Status.choices],
                                      required=False)

    def clean(self):
        cleaned = super().clean()
        start, end = cleaned.get('created_from'), cleaned.get('created_to')
        if start and end and start > end:
            raise ValidationError('Created from must be on or before Created to.')
        return cleaned
