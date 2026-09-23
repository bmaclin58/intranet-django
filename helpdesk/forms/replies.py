"""Public conversation replies containing text, attachments, or both."""
from iommi import Field, Form

from .shared import FORM_STYLE, attachment_field, bounded_text, validate_files


def reply_form (handler) :
	def validate (form, **_) :
		validate_files (form)
		if form.is_valid () and not form.fields.body.value and not form.fields.attachments.value :
			form.add_error ('Enter a reply or attach a file.')

	return Form (
			iommi_style = FORM_STYLE,
			attrs__class__helpdesk_form = True,
			attrs__enctype = 'multipart/form-data',

			fields = dict (
				body = Field.textarea (
					display_name = 'Your reply',
					required = False,
					attrs__class__wide = True,
					input__attrs__rows = 4,
					input__attrs__maxlength = 10000,
					is_valid = bounded_text,
                        ),
				attachments = attachment_field (),
                    ),

			post_validation = validate,
			actions__submit__display_name = 'Send reply',
			actions__submit__post_handler = handler,
			)
