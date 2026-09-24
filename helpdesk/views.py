"""Employee ticket pages, public conversations, and authorized file downloads."""
import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.paginator import Paginator
from django.core.validators import validate_email
from django.db import DatabaseError, transaction
from django.db.models import Q
from django.http import FileResponse, Http404, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_GET, require_http_methods

from .forms.emails.email_handler import send_ticket_created_emails, urgency_notification
from .forms import reply_form, snapshot_answers, ticket_form
from .models import Category, Ticket, TicketAttachment, TicketComment, TicketType
from .permissions import can_handle_tickets, visible_tickets
from .services import save_ticket_activity

logger = logging.getLogger(__name__)


def dispatch_form(request, form) :
	# iommi expects exactly one known action marker on POST; reject malformed requests.
	if request.method == 'POST' :
		markers = [key for key in request.POST if key.startswith('-')]
		if markers != [form.actions.submit.own_target_marker()] :
			return HttpResponseBadRequest('Invalid form action.')
	return form.perform_dispatch()


@login_required
@require_GET
def index(request) :
	tickets = Ticket.objects.filter(requester = request.user).select_related('ticket_type', 'assignee')
	query = request.GET.get('q', '').strip()[:200]
	status = request.GET.get('status', '')
	if query :
		tickets = tickets.filter(Q(subject__icontains = query) | Q(description__icontains = query))
	if status in Ticket.Status.values :
		tickets = tickets.filter(status = status)
	return render(
			request, 'helpdesk/index.html', {
					'page'   : Paginator(tickets, 20).get_page(request.GET.get('page')),
					'query'  : query,
					'status' : status, 'statuses' : Ticket.Status.choices, 'nav' : 'tickets',
					},
			)


@login_required
@require_GET
def choose(request) :
	from django.db.models import Prefetch

	categories = Category.objects.filter(active = True, ticket_types__active = True).distinct().prefetch_related(
			Prefetch('ticket_types', queryset = TicketType.objects.filter(active = True)),
			)
	return render(request, 'helpdesk/choose.html', {'categories' : categories, 'nav' : 'new'})


@login_required
@require_http_methods(["GET", "POST"])
def create(request, type_id) :
	kind = get_object_or_404(
			TicketType.objects.select_related("category"),
			pk = type_id,
			active = True,
			category__active = True,
			)

	def submit(form, **_) :
		if not form.is_valid() :
			return None

		requester_email = (request.user.email or "").strip()
		try :
			validate_email(requester_email)
		except ValidationError :
			form.add_error(
					"Your account needs a valid email address before you can "
					"submit a ticket. Please ask IT to update your account.",
					)
			return None

		ticket = Ticket(
				category = kind.category,
				ticket_type = kind,
				requester = request.user,
				requester_email = requester_email,
				subject = form.fields.subject.value,
				description = form.fields.description.value,
				priority = form.fields.priority.value,
				answers = snapshot_answers(form, definitions),
				)
		try :
			save_ticket_activity(
					ticket, request.user, form.fields.attachments.value or [],
					)
		except (OSError, DatabaseError) :
			logger.exception("Ticket submission failed")
			form.add_error(
					"Your ticket could not be saved. Please try again. "
					"Re-select any attachments.",
					)
			return None

		ticket_url = request.build_absolute_uri(
				reverse("helpdesk:detail", kwargs = {"pk" : ticket.pk}),
				)

		def notify() :
			# triggers on django.db.transaction
			send_ticket_created_emails(ticket.pk, ticket_url)

			if ticket.priority in ['High', 'Urgent']:
				mngment_Email = request.user.manager
				urgency_notification(ticket.pk, ticket_url, mngment_Email)

		transaction.on_commit(notify, robust = True)
		messages.success(request, f"{ticket.number} was submitted to IT.")
		return redirect("helpdesk:detail", pk = ticket.pk)

	unbound, definitions = ticket_form(kind, submit)
	form = unbound.bind(request = request)
	response = dispatch_form(request, form)
	if response is not None :
		return response
	context = {
			'form'                   : form,
			'kind'                   : kind,
			'nav'                    : 'new',
			'knowledge_base_tickets' : [
					(
							'Internet Connectivity',
							'https://servicedesk.standardcal.com/solutions/1589814-troubleshooting-internet-issues'
							'.portal',
							),
					(
							'VPN',
							'https://servicedesk.standardcal.com/solutions/1589975-establishing-a-vpn-connection-for'
							'-mac',
							),
					],
			}
	return render(request, 'helpdesk/create.html', context)


@login_required
@require_http_methods(['GET', 'POST'])
def detail(request, pk) :
	ticket = get_object_or_404(visible_tickets(request.user), pk = pk)
	is_owner = ticket.requester_id == request.user.pk
	can_reply = is_owner or (can_handle_tickets(request.user) and request.user.has_perms(
			['helpdesk.change_ticket', 'helpdesk.add_ticketcomment'],
			))

	def submit(form, **_) :
		if not can_reply :
			raise PermissionDenied
		if not form.is_valid() :
			return None
		comment = TicketComment(
				ticket = ticket, author = request.user, body = form.fields.body.value or '', internal = False,
				)
		if form.fields.attachments.value and not is_owner and not request.user.has_perm(
				'helpdesk.add_ticketattachment',
				) :
			raise PermissionDenied
		try :
			save_ticket_activity(ticket, request.user, form.fields.attachments.value or [], comment = comment)
		except (OSError, DatabaseError) :
			logger.exception('Ticket reply failed')
			form.add_error('Your reply could not be saved. Please try again. Re-select any attachments.')
			return None
		messages.success(request, 'Your reply was added.')
		return redirect('helpdesk:detail', pk = ticket.pk)

	if request.method == 'POST' and not can_reply :
		raise PermissionDenied
	form = reply_form(submit).bind(request = request) if can_reply else None
	if form is not None :
		response = dispatch_form(request, form)
		if response is not None :
			return response
	# Portal is always the employee-visible conversation, even when IT visits it.
	comments = ticket.comments.filter(internal = False).select_related('author').prefetch_related('attachments')
	return render(
			request, 'helpdesk/detail.html', {
					'ticket'      : ticket, 'comments' : comments, 'form' : form,
					'attachments' : ticket.attachments.filter(comment__isnull = True), 'nav' : 'tickets',
					},
			)


@login_required
@require_GET
def attachment(request, pk) :
	item = get_object_or_404(
			TicketAttachment.objects.select_related('comment', 'ticket'), pk = pk,
			ticket__in = visible_tickets(request.user),
			)
	if item.ticket.requester_id != request.user.pk and not request.user.has_perm('helpdesk.view_ticketattachment') :
		raise Http404
	if item.comment_id and item.comment.internal and not (
			can_handle_tickets(request.user) and request.user.has_perm('helpdesk.view_ticketcomment')) :
		raise Http404
	try :
		file = item.file.open('rb')
	except (OSError, ValueError) as exc :
		raise Http404('Attachment unavailable.') from exc
	response = FileResponse(
			file, as_attachment = True, filename = item.original_name, content_type = 'application/octet-stream',
			)
	response['X-Content-Type-Options'] = 'nosniff'
	response['Cache-Control'] = 'private, no-store'
	return response
