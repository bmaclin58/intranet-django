import hashlib
import json
from decimal import Decimal

from django import forms as django_forms
from django.core.exceptions import ValidationError
from django.core.serializers.json import DjangoJSONEncoder
from django.conf import settings
from django.urls import reverse
from iommi import Field, Form, Style
from iommi.style_base import base

from .models import Category, Ticket
from .uploads import validate_uploads


FORM_STYLE = Style(
    base,
    Field=dict(template='helpdesk/field.html',
               attrs__class__hd_field=True,
               input__attrs__required=lambda field, **_: 'required' if field.required and not field.is_list else None,
               input__attrs__aria_required=lambda field, **_: 'true' if field.required else None),
    Form=dict(template='helpdesk/iommi_form.html'),
    Action=dict(attrs__class__button=True),
)

# The only permitted input factories. Admin data never names Python code or templates.
FIELD_FACTORIES = {
    'text': Field.text,
    'textarea': Field.textarea,
    'email': Field.email,
    'integer': Field.integer,
    'decimal': Field.decimal,
    'date': Field.date,
    'checkbox': Field.boolean,
    'dropdown': Field.choice,
    'multiple_choice': Field.checkboxes,
}


def definition_data(ticket_type):
    return {'type': ticket_type.pk,
            'name': ticket_type.name,
            'active': ticket_type.active,
            'category': ticket_type.category_id,
            'category_active': ticket_type.category.active,
            'fields': list(ticket_type.fields.filter(active=True).values(
                'id', 'label', 'field_type', 'required', 'help_text', 'choices', 'position'))}


def definition_token(ticket_type):
    return hashlib.sha256(json.dumps(definition_data(ticket_type), sort_keys=True).encode()).hexdigest()


def bounded_text(parsed_data, **_):
    return (parsed_data is None or len(parsed_data) <= 10000, 'Use no more than 10,000 characters.')


def custom_valid(field, parsed_data, **_):
    required_checkbox = field.extra.get('required_checkbox', False)
    if required_checkbox and parsed_data is not True:
        return False, 'This checkbox must be checked.'
    if isinstance(parsed_data, Decimal) and not parsed_data.is_finite():
        return False, 'Enter a finite number.'
    if isinstance(parsed_data, str) and len(parsed_data) > field.extra.get('max_length', 10000):
        return False, 'This answer is too long.'
    return True, ''


def attachment_field():
    return Field.file(
        required=False, is_list=True, display_name='Attachments', template='helpdesk/field.html',
        attrs__class__wide=True, input__attrs__accept='.png,.jpg,.jpeg,.pdf,.txt,.docx,.xlsx',
        help_text=f'Screenshots or documents. Up to {settings.HELPDESK_MAX_FILES} files, {settings.HELPDESK_MAX_FILE_SIZE // (1024 * 1024)} MB each.',
    )


def validate_files(form, **_):
    if form.is_valid():
        try:
            validate_uploads(form.fields.attachments.value or [])
        except ValidationError as exc:
            for error in exc.messages:
                form.fields.attachments.add_error(error)


def ticket_form(ticket_type, handler=None, preview=False):
    definitions = list(ticket_type.fields.filter(active=True))
    fields = {
        'definition': Field.hidden(initial=definition_token(ticket_type)),
        'subject': Field.text(display_name='Subject', attrs__class__wide=True,
                              input__attrs__placeholder='Briefly describe the issue', input__attrs__maxlength=200,
                              is_valid=lambda parsed_data, **_: (parsed_data is None or len(parsed_data) <= 200, 'Use no more than 200 characters.')),
        'description': Field.textarea(display_name='Description', attrs__class__wide=True,
                                     input__attrs__placeholder='What happened, and what have you tried?',
                                     input__attrs__rows=5, input__attrs__maxlength=10000, is_valid=bounded_text),
        'priority': Field.choice(choices=[x for x, _ in Ticket.Priority.choices], initial=Ticket.Priority.NORMAL,
                                 choice_display_name_formatter=lambda choice, **_: Ticket.Priority(choice).label),
    }
    for definition in definitions:
        options = dict(display_name=definition.label, required=definition.required, help_text=definition.help_text)
        if definition.field_type in ('dropdown', 'multiple_choice'):
            options['choices'] = definition.options
            options['empty_label'] = 'Choose an option'
            if definition.field_type == 'dropdown' and definition.required:
                options['choices'] = ['', *definition.options]
                options['initial'] = ''
                options['choice_display_name_formatter'] = lambda choice, **_: choice or 'Choose an option'
        else:
            options['is_valid'] = custom_valid
            options['extra__required_checkbox'] = definition.field_type == 'checkbox' and definition.required
            options['extra__max_length'] = 10000 if definition.field_type == 'textarea' else 1000
        if definition.field_type == 'textarea':
            options.update(attrs__class__wide=True, input__attrs__rows=4, input__attrs__maxlength=10000)
        fields[f'custom_{definition.pk}'] = FIELD_FACTORIES[definition.field_type](**options)
    fields['attachments'] = attachment_field()

    def validate(form, **_):
        validate_files(form)
        if form.get_request().method == 'POST' and form.fields.definition.value != definition_token(ticket_type):
            form.add_error('This form has changed. Review the updated fields and submit again.')
            form.fields.definition.input.attrs.value = definition_token(ticket_type)

    form = Form(fields=fields, iommi_style=FORM_STYLE, post_validation=validate,
                extra__cancel_url=reverse('helpdesk:index') if not preview else None,
                actions__submit__display_name='Submit ticket',
                actions__submit__post_handler=handler, actions__submit__include=not preview,
                attrs__class__helpdesk_form=True, attrs__enctype='multipart/form-data')
    return form, definitions


def snapshot_answers(form, definitions):
    answers = [{'field_id': definition.pk, 'label': definition.label, 'type': definition.field_type,
                'required': definition.required, 'options': definition.options,
                'help_text': definition.help_text, 'position': definition.position, 'active': definition.active,
                'value': form.fields[f'custom_{definition.pk}'].value} for definition in definitions]
    return json.loads(json.dumps(answers, cls=DjangoJSONEncoder))


def reply_form(handler):
    def validate(form, **_):
        validate_files(form)
        if form.is_valid() and not form.fields.body.value and not form.fields.attachments.value:
            form.add_error('Enter a reply or attach a file.')
    return Form(
        iommi_style=FORM_STYLE, attrs__class__helpdesk_form=True, attrs__enctype='multipart/form-data',
        fields=dict(body=Field.textarea(display_name='Your reply', required=False, attrs__class__wide=True,
                                        input__attrs__rows=4, input__attrs__maxlength=10000, is_valid=bounded_text),
                    attachments=attachment_field()),
        post_validation=validate, actions__submit__display_name='Send reply', actions__submit__post_handler=handler,
    )


class ReportFilters(django_forms.Form):
    created_from = django_forms.DateField(required=False, widget=django_forms.DateInput(attrs={'type': 'date'}))
    created_to = django_forms.DateField(required=False, widget=django_forms.DateInput(attrs={'type': 'date'}))
    category = django_forms.ModelChoiceField(queryset=Category.objects.all(), required=False, empty_label='All categories')
    status = django_forms.ChoiceField(choices=[('', 'All statuses'), *Ticket.Status.choices], required=False)

    def clean(self):
        cleaned = super().clean()
        start, end = cleaned.get('created_from'), cleaned.get('created_to')
        if start and end and start > end:
            raise ValidationError('Created from must be on or before Created to.')
        return cleaned
