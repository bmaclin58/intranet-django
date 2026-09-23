"""Staff-only form preview and reports, wrapped by admin.py's admin_site.admin_view."""
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.views.decorators.http import require_GET

from .forms import ReportFilters, ticket_form
from .models import Ticket, TicketType


@require_GET
def preview(request, type_id, model_admin):
    if not model_admin.has_view_permission(request):
        raise PermissionDenied
    kind = get_object_or_404(TicketType.objects.select_related('category'), pk=type_id)
    unbound, _ = ticket_form(kind, preview=True)
    return render(request, 'helpdesk/create.html', {'form': unbound.bind(request=request), 'kind': kind, 'preview': True, 'nav': 'new'})


@require_GET
def reports(request, model_admin):
    if not request.user.has_perms(['helpdesk.view_ticket', 'helpdesk.view_reports']):
        raise PermissionDenied
    filters = ReportFilters(request.GET)
    tickets = Ticket.objects.select_related('category', 'assignee')
    if filters.is_valid():
        data = filters.cleaned_data
        if data['created_from']:
            tickets = tickets.filter(created_at__date__gte=data['created_from'])
        if data['created_to']:
            tickets = tickets.filter(created_at__date__lte=data['created_to'])
        if data['category']:
            tickets = tickets.filter(category=data['category'])
        if data['status']:
            tickets = tickets.filter(status=data['status'])
    else:
        tickets = tickets.none()
    totals = tickets.aggregate(total=Count('pk'), open=Count('pk', filter=Q(status__in=Ticket.OPEN_STATUSES)),
                               unassigned=Count('pk', filter=Q(status__in=Ticket.OPEN_STATUSES, assignee__isnull=True)),
                               finished=Count('pk', filter=Q(status__in=[Ticket.Status.RESOLVED, Ticket.Status.CLOSED])))
    by_category = tickets.order_by().values('category__name').annotate(count=Count('pk')).order_by('category__name')
    by_status = list(tickets.order_by().values('status').annotate(count=Count('pk')).order_by('status'))
    for row in by_status:
        row['label'] = Ticket.Status(row['status']).label
    context = {**model_admin.admin_site.each_context(request), 'title': 'Ticket reports', 'filters': filters,
               'totals': totals, 'by_category': by_category, 'by_status': by_status,
               'page': Paginator(tickets, 25).get_page(request.GET.get('page')),
               'opts': Ticket._meta, 'report_url': reverse('admin:helpdesk_ticket_reports')}
    return render(request, 'admin/helpdesk/reports.html', context)
