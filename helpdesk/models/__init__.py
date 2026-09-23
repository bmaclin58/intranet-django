"""Register all helpdesk models and preserve existing model and migration imports."""
from .definitions import Category, TicketField, TicketType
from .tickets import Ticket
from .activity import TicketAttachment, TicketComment, attachment_path, private_storage

__all__ = [
    'Category', 'TicketType', 'TicketField', 'Ticket', 'TicketComment', 'TicketAttachment',
    'private_storage', 'attachment_path',
]
