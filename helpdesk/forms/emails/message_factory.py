from django.utils import timezone

from helpdesk.models import Ticket

def format_answer(value: object) -> str :
	if value is None or value == "" :
		return "(not provided)"
	if isinstance(value, bool) :
		return "Yes" if value else "No"
	if isinstance(value, list) :
		return ", ".join(str(item) for item in value) or "(none)"
	return str(value)


def generate_msg_from_Form(ticket,
                           ticket_url,
                           high_priority = False) :
	# 1. Check if the form parsed cleanly

	requester_name = (
			ticket.requester.get_full_name() or ticket.requester.get_username()
	)

	answers = [
			f"{answer['label']}: {format_answer(answer.get('value'))}"
			for answer in ticket.answers
			]

	created_at = timezone.localtime(ticket.created_at)

	body = [
					"A helpdesk ticket has been submitted.",
					"",
					f"Ticket number: {ticket.number}",
					f"Subject: {ticket.subject}",
					f"Submitted by: {requester_name}",
					f"Email: {ticket.requester_email}",
					f"Category: {ticket.category_label}",
					f"Request type: {ticket.type_label}",
					f"Priority: {ticket.get_priority_display()}",
					f"Status: {ticket.get_status_display()}",
					f"Submitted: {created_at:%Y-%m-%d %H:%M %Z}",
					"",
					"Description:",
					ticket.description,
					"",
					"Additional details:",
					*(answers or ["(none)"]),
					"",
					f"View ticket: {ticket_url}",
					"Attachments and conversation history are available in the portal.",
					]

	if high_priority :
		# This prepends multiple items to the start of the list
		body[0 :0] = [
				f"A High Priority Ticket has been submitted from {ticket.requester_email}",
				"Please see below for more details:",
				]

	body = "\n".join(body)

	return body