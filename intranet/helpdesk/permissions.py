from django.contrib.auth import get_user_model
from django.db.models import Q

from .models import Ticket


def can_handle_tickets(user):
    return user.is_active and user.is_staff and user.has_perm('helpdesk.view_ticket')


def visible_tickets(user):
    tickets = Ticket.objects.select_related('category', 'ticket_type', 'requester', 'assignee')
    return tickets if can_handle_tickets(user) else tickets.filter(requester=user)


def eligible_assignees():
    permission = Q(user_permissions__content_type__app_label='helpdesk', user_permissions__codename='change_ticket')
    group_permission = Q(groups__permissions__content_type__app_label='helpdesk', groups__permissions__codename='change_ticket')
    return get_user_model().objects.filter(is_active=True, is_staff=True).filter(Q(is_superuser=True) | permission | group_permission).distinct()
