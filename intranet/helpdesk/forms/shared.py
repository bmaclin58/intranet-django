"""Shared iommi styling, text limits, attachment input, and file validation."""
from django.conf import settings
from django.core.exceptions import ValidationError
from iommi import Field, Style
from iommi.style_base import base

from ..uploads import validate_uploads


FORM_STYLE = Style(
    base,
    Field=dict(template='helpdesk/field.html',
               attrs__class__hd_field=True,
               input__attrs__required=lambda field, **_: 'required' if field.required and not field.is_list else None,
               input__attrs__aria_required=lambda field, **_: 'true' if field.required else None),
    Form=dict(template='helpdesk/iommi_form.html'),
    Action=dict(attrs__class__button=True),
)


def bounded_text(parsed_data, **_):
    return (parsed_data is None or len(parsed_data) <= 10000, 'Use no more than 10,000 characters.')


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
