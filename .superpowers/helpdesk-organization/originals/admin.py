from django.contrib import admin
from django import forms
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin, GroupAdmin as DjangoGroupAdmin
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.template.loader import render_to_string
from django.urls import path, reverse
from django.utils.html import format_html
from unfold.admin import ModelAdmin, TabularInline
from unfold.forms import AdminPasswordChangeForm, UserChangeForm, UserCreationForm

from .models import Category, Ticket, TicketAttachment, TicketComment, TicketField, TicketType
from .permissions import eligible_assignees
from . import views


@admin.register(Category)
class CategoryAdmin(ModelAdmin):
    list_display = ['name', 'position', 'active']
    list_filter = ['active']
    search_fields = ['name']


class TicketFieldInline(TabularInline):
    model = TicketField
    fields = ['label', 'field_type', 'required', 'help_text', 'choices', 'position', 'active']
    extra = 0
    ordering = ['position', 'pk']


@admin.register(TicketType)
class TicketTypeAdmin(ModelAdmin):
    list_display = ['name', 'category', 'active', 'preview_link']
    list_filter = ['category', 'active']
    search_fields = ['name']
    inlines = [TicketFieldInline]
    readonly_fields = ['preview_link']
    fields = ['category', 'name', 'description', 'position', 'active', 'preview_link']

    @admin.display(description='Form preview')
    def preview_link(self, obj):
        if not obj or not obj.pk:
            return 'Save this ticket type, add fields, then preview it.'
        return format_html('<a href="{}">Preview saved form</a>', reverse('admin:helpdesk_tickettype_preview', args=[obj.pk]))

    def get_urls(self):
        return [path('<int:type_id>/preview/', self.admin_site.admin_view(
            lambda request, type_id: views.preview(request, type_id, self)),
            name='helpdesk_tickettype_preview')] + super().get_urls()


class CommentForm(forms.ModelForm):
    class Meta:
        model = TicketComment
        fields = ['body', 'internal']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['body'].required = not self.instance.pk
        if self.instance.pk:
            for field in self.fields.values():
                field.disabled = True


class CommentInline(TabularInline):
    model = TicketComment
    form = CommentForm
    fields = ['body', 'internal', 'author', 'created_at']
    readonly_fields = ['author', 'created_at']
    extra = 1
    can_delete = False
    verbose_name_plural = 'Conversation — add a public reply or internal note'


class AttachmentInline(TabularInline):
    model = TicketAttachment
    fields = ['download', 'size', 'uploader', 'created_at']
    readonly_fields = fields
    extra = 0
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False

    @admin.display(description='Attachment')
    def download(self, obj):
        return format_html('<a href="{}">{}</a>', reverse('helpdesk:attachment', args=[obj.pk]), obj.original_name)


@admin.register(Ticket)
class TicketAdmin(ModelAdmin):
    list_display = ['number', 'subject', 'requester', 'category', 'status', 'priority', 'assignee', 'created_at']
    list_filter = ['status', 'priority', 'category', 'ticket_type', 'assignee']
    search_fields = ['subject', 'description', 'requester__username', 'requester__email']
    list_select_related = ['requester', 'category', 'ticket_type', 'assignee']
    date_hierarchy = 'created_at'
    inlines = [CommentInline, AttachmentInline]
    readonly_fields = ['number', 'subject', 'description', 'requester', 'category_label', 'type_label',
                       'submitted_answers', 'created_at', 'updated_at', 'resolved_at', 'closed_at', 'portal_link']
    fieldsets = [
        ('Ticket', {'fields': ['number', 'subject', 'status', 'priority', 'assignee', 'portal_link']}),
        ('Submitted request', {'fields': ['requester', 'category_label', 'type_label', 'description', 'submitted_answers']}),
        ('Dates', {'fields': ['created_at', 'updated_at', 'resolved_at', 'closed_at']}),
    ]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    @admin.display(description='Custom answers')
    def submitted_answers(self, obj):
        return render_to_string('helpdesk/answers.html', {'answers': obj.answers})

    @admin.display(description='Employee conversation')
    def portal_link(self, obj):
        return format_html('<a href="{}">Open public conversation / attach files</a>', reverse('helpdesk:detail', args=[obj.pk]))

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'assignee':
            kwargs['queryset'] = eligible_assignees()
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def save_formset(self, request, form, formset, change):
        instances = formset.save(commit=False)
        for instance in instances:
            if isinstance(instance, TicketComment) and not instance.pk:
                instance.author = request.user
            instance.save()
        formset.save_m2m()

    def get_urls(self):
        return [path('reports/', self.admin_site.admin_view(lambda request: views.reports(request, self)),
                     name='helpdesk_ticket_reports')] + super().get_urls()


# Reuse Django's account management with the already-installed Unfold widgets.
User = get_user_model()
admin.site.unregister(User)
admin.site.unregister(Group)

@admin.register(User)
class UserAdmin(DjangoUserAdmin, ModelAdmin):
    form = UserChangeForm
    add_form = UserCreationForm
    change_password_form = AdminPasswordChangeForm


@admin.register(Group)
class GroupAdmin(DjangoGroupAdmin, ModelAdmin):
    pass
