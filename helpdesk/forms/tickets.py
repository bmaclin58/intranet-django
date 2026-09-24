"""Build dynamic ticket forms, detect changed definitions, and snapshot answers."""
import hashlib
import json
from decimal import Decimal

from django.core.serializers.json import DjangoJSONEncoder
from django.urls import reverse
from iommi import Field, Form

from ..models import Ticket
from .shared import FORM_STYLE, attachment_field, bounded_text, validate_files
from ..models.definitions import ApprovedSoftware, CurrentHardware
from ..models.tickets import MAX_TEXT_LENGTH

DYNAMIC_FIELD_NAMES = ['Approved SCI Software','Hardware Item']

# The only permitted input factories. Admin data never names Python code or templates.
FIELD_FACTORIES = {
		'text'            : Field.text,
		'textarea'        : Field.textarea,
		'email'           : Field.email,
		'phone'           : Field.phone_number,
		'integer'         : Field.integer,
		'decimal'         : Field.decimal,
		'date'            : Field.date,
		'checkbox'        : Field.boolean,
		'dropdown'        : Field.choice,
		'multiple_choice' : Field.checkboxes,
		}


def definition_data (ticket_type) :
	return {
			'type'            : ticket_type.pk,
			'name'            : ticket_type.name,
			'active'          : ticket_type.active,
			'category'        : ticket_type.category_id,
			'category_active' : ticket_type.category.active,
			'fields'          : list (
					ticket_type.fields.filter (active = True).values (
							'id', 'label', 'field_type', 'required', 'help_text', 'choices', 'position',
							),
					),
			}


def definition_token (ticket_type) :
	return hashlib.sha256 (json.dumps (definition_data (ticket_type), sort_keys = True).encode ()).hexdigest ()


def custom_valid (field, parsed_data, **_) :
	required_checkbox = field.extra.get ('required_checkbox', False)

	if required_checkbox and parsed_data is not True :
		return False, 'This checkbox must be checked.'

	if isinstance (parsed_data, Decimal) and not parsed_data.is_finite () :
		return False, 'Enter a finite number.'

	if isinstance (parsed_data, str) and len (parsed_data) > field.extra.get ('max_length', MAX_TEXT_LENGTH) :
		return False, 'This answer is too long.'

	return True, ''


def ticket_form (ticket_type, handler = None, preview = False) :
	definitions = list (ticket_type.fields.filter (active = True))

	fields = {
			'definition'  : Field.hidden (initial = definition_token (ticket_type)),
			'subject'     : Field.text (
					display_name = 'Subject',
					attrs__class__wide = True,
					input__attrs__placeholder = 'Briefly describe the issue',
					input__attrs__maxlength = 200,
					is_valid = lambda parsed_data, **_ : (
							parsed_data is None or len (parsed_data) <= 200, 'Use no more than 200 characters.',
							),
					),

			'description' : Field.textarea (
					display_name = 'Description',
					attrs__class__wide = True,
					input__attrs__placeholder = 'What happened, and what have you tried?',
					input__attrs__rows = 5,
					input__attrs__maxlength = MAX_TEXT_LENGTH,
					is_valid = bounded_text,
					),

			'priority'    : Field.choice (
					choices = [x for x, _ in Ticket.Priority.choices],
					initial = Ticket.Priority.NORMAL,
					choice_display_name_formatter = lambda choice, **_ : Ticket.Priority (choice).label,
					),

			'dept'        : Field.choice (
					choices = [x for x, _ in Ticket.Dept.choices],
					initial = Ticket.Dept.BLANK,
					choice_display_name_formatter = lambda choice, **_ : Ticket.Dept (choice).label,
					),
			}

	for definition in definitions :
		options = dict(
				display_name = definition.label,
				required = definition.required,
				help_text = definition.help_text,
				)

		if definition.field_type in ('dropdown', 'multiple_choice') :
			options['choices'] = definition.options
			options['empty_label'] = 'Choose an option'

			# Check for the specific database-backed field first
			if definition.field_type == 'dropdown' and definition.required and definition.label in DYNAMIC_FIELD_NAMES :
				if definition.label == 'Approved SCI Software' :
					# Fetch unique software names as a flat list of strings
					choices = list(ApprovedSoftware.objects.values_list('software_Name', flat = True).distinct())

				elif definition.label == 'Hardware Item':
					# Fetch unique hardware items
					choices = list(CurrentHardware.objects.values_list('hardware_Name', flat = True).distinct())

				# Pass a flat list of strings, adding the empty option up front just like the block below
				options['choices'] = ['', *choices]
				options['empty_label'] = 'Choose an option'
				options['initial'] = ''
				options['choice_display_name_formatter'] = lambda choice, **_ : choice or 'Choose an option'

			# Use 'elif' so standard required dropdowns don't overwrite the code above
			elif definition.field_type == 'dropdown' and definition.required :
				options['choices'] = ['', *definition.options]
				options['initial'] = ''
				options['choice_display_name_formatter'] = lambda choice, **_ : choice or 'Choose an option'

		else :
			options ['is_valid'] = custom_valid
			options ['extra__required_checkbox'] = definition.field_type == 'checkbox' and definition.required
			options ['extra__max_length'] = MAX_TEXT_LENGTH if definition.field_type == 'textarea' else 1000

		if definition.field_type == 'textarea' :
			options.update (attrs__class__wide = True, input__attrs__rows = 4, input__attrs__maxlength = 10000)
		fields [f'custom_{definition.pk}'] = FIELD_FACTORIES [definition.field_type] (**options)
	fields ['attachments'] = attachment_field ()

	def validate (form, **_) :
		validate_files (form)
		if form.get_request ().method == 'POST' and form.fields.definition.value != definition_token (ticket_type) :
			form.add_error ('This form has changed. Review the updated fields and submit again.')
			form.fields.definition.input.attrs.value = definition_token (ticket_type)

	form = Form (
			fields = fields,
			iommi_style = FORM_STYLE,
			post_validation = validate,
			extra__cancel_url = reverse ('helpdesk:index') if not preview else None,
			actions__submit__display_name = 'Submit ticket',
			actions__submit__post_handler = handler,
			actions__submit__include = not preview,
			attrs__class__helpdesk_form = True,
			attrs__enctype = 'multipart/form-data',
			)
	return form, definitions


def snapshot_answers (form, definitions) :
	answers = [{
			'field_id'  : definition.pk,
			'label'     : definition.label,
			'type'      : definition.field_type,
			'required'  : definition.required,
			'options'   : definition.options,
			'help_text' : definition.help_text,
			'position'  : definition.position,
			'active'    : definition.active,
			'value'     : form.fields [f'custom_{definition.pk}'].value,
			} for definition in definitions]
	return json.loads (json.dumps (answers, cls = DjangoJSONEncoder))
