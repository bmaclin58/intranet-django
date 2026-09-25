import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import patch
from zoneinfo import ZoneInfo

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.files.storage import FileSystemStorage
from django.db.models.deletion import ProtectedError
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from .models import Category, Ticket, TicketAttachment, TicketComment, TicketField, TicketType
from .forms import definition_token
from .uploads import validate_uploads


class HelpdeskTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.employee = User.objects.create_user('employee', password='test-password-123')
        cls.other = User.objects.create_user('other', password='test-password-123')
        cls.staff = User.objects.create_user('staff', password='test-password-123', is_staff=True)
        cls.admin = User.objects.create_superuser('admin', 'admin@example.test', 'test-password-123')
        cls.category = Category.objects.create(name='Testing')
        cls.kind = TicketType.objects.create(category=cls.category, name='Test request')
        cls.field = TicketField.objects.create(ticket_type=cls.kind, label='Asset', field_type='text', required=True)

    def setUp(self):
        self.media = tempfile.TemporaryDirectory()
        self.addCleanup(self.media.cleanup)
        setting = override_settings(HELPDESK_UPLOAD_ROOT=Path(self.media.name))
        setting.enable()
        self.addCleanup(setting.disable)
        storage_patch = patch.object(TicketAttachment._meta.get_field('file'), 'storage', FileSystemStorage(location=self.media.name))
        storage_patch.start()
        self.addCleanup(storage_patch.stop)
        self.client.force_login(self.employee)

    def payload(self, **updates):
        data = {'subject': 'Laptop issue', 'description': 'The screen is blank.', 'priority': 'normal',
                'definition': definition_token(self.kind), f'custom_{self.field.pk}': 'SCI-1042', '-submit': ''}
        data.update(updates)
        return data

    def submit(self, **updates):
        return self.client.post(reverse('helpdesk:create', args=[self.kind.pk]), self.payload(**updates))

    def ticket(self):
        return Ticket.objects.create(category=self.category, ticket_type=self.kind, requester=self.employee,
                                     subject='Existing issue', description='Details')

    def test_submit_invalid_and_valid_server_owned_values(self):
        self.assertEqual(self.submit(subject='').status_code, 200)
        self.assertEqual(Ticket.objects.count(), 0)
        self.assertEqual(self.submit(requester=self.other.pk, status='closed', assignee=self.admin.pk).status_code, 302)
        ticket = Ticket.objects.get()
        self.assertEqual(ticket.requester, self.employee)
        self.assertEqual(ticket.status, 'new')
        self.assertIsNone(ticket.assignee)
        self.assertEqual(ticket.answers[0]['value'], 'SCI-1042')

    def test_all_field_types_and_invalid_values(self):
        cases = [('text', 'hello', 'hello'), ('textarea', 'long text', 'long text'),
                 ('email', 'a@example.test', 'a@example.test'), ('integer', '4', 4),
                 ('decimal', '4.25', '4.25'), ('date', '2026-09-22', '2026-09-22'),
                 ('checkbox', 'on', True), ('dropdown', 'One', 'One'),
                 ('multiple_choice', ['One', 'Two'], ['One', 'Two'])]
        for field_type, value, expected in cases:
            with self.subTest(field_type=field_type):
                self.field.field_type = field_type
                self.field.choices = 'One\nTwo' if field_type in ('dropdown', 'multiple_choice') else ''
                self.field.save()
                response = self.submit(**{f'custom_{self.field.pk}': value})
                self.assertEqual(response.status_code, 302, response.content[:500])
                self.assertEqual(Ticket.objects.latest('pk').answers[0]['value'], expected)
        for field_type, value in [('email', 'bad'), ('integer', '1.2'), ('decimal', 'NaN'),
                                  ('date', 'bad'), ('checkbox', ''), ('dropdown', 'Forged'),
                                  ('multiple_choice', ['One', 'Forged'])]:
            with self.subTest(invalid=field_type):
                self.field.field_type = field_type
                self.field.choices = 'One\nTwo' if field_type in ('dropdown', 'multiple_choice') else ''
                self.field.save()
                count = Ticket.objects.count()
                self.assertEqual(self.submit(**{f'custom_{self.field.pk}': value}).status_code, 200)
                self.assertEqual(Ticket.objects.count(), count)

    def test_stale_definition_and_historical_snapshot(self):
        old = self.payload()
        self.field.label = 'Device identifier'
        self.field.help_text = 'Printed below the barcode.'
        self.field.save()
        response = self.client.post(reverse('helpdesk:create', args=[self.kind.pk]), old)
        self.assertContains(response, 'form has changed')
        self.assertFalse(Ticket.objects.exists())
        self.submit()
        ticket = Ticket.objects.get()
        self.field.delete()
        ticket.refresh_from_db()
        self.assertEqual(ticket.answers[0]['label'], 'Device identifier')
        self.assertEqual(ticket.answers[0]['help_text'], 'Printed below the barcode.')
        with self.assertRaises(ProtectedError):
            self.kind.delete()

    def test_inactive_types_and_categories(self):
        self.kind.active = False
        self.kind.save()
        self.assertEqual(self.submit().status_code, 404)

        TicketType.objects.update(active=False)
        self.assertContains(self.client.get(reverse('helpdesk:choose')), 'No request forms are available yet')
        self.kind.active = True
        self.kind.save()
        self.category.active = False
        self.category.save()
        self.assertEqual(self.submit().status_code, 404)

    def test_ownership_internal_notes_and_reply(self):
        ticket = self.ticket()
        TicketComment.objects.create(ticket=ticket, author=self.admin, body='Private diagnostic', internal=True)
        url = reverse('helpdesk:detail', args=[ticket.pk])
        self.assertNotContains(self.client.get(url), 'Private diagnostic')
        self.assertEqual(self.client.post(url, {'body': 'More detail', 'internal': 'on', '-submit': ''}).status_code, 302)
        self.assertFalse(TicketComment.objects.get(body='More detail').internal)
        for user in [self.other, self.staff]:
            self.client.force_login(user)
            self.assertEqual(self.client.get(url).status_code, 404)
            self.assertEqual(self.client.post(url, {'body': 'attack', '-submit': ''}).status_code, 404)

    def test_upload_and_protected_download(self):
        self.assertEqual(self.submit(attachments=SimpleUploadedFile('notes.txt', b'Useful diagnostic')).status_code, 302)
        attachment = TicketAttachment.objects.get()
        url = reverse('helpdesk:attachment', args=[attachment.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertIn('attachment;', response['Content-Disposition'])
        self.assertEqual(response['X-Content-Type-Options'], 'nosniff')
        response.close()
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(url).status_code, 404)
        self.client.logout()
        self.assertEqual(self.client.get(url).status_code, 302)

    def test_invalid_uploads_and_cleanup_on_failure(self):
        for name, content in [('bad.exe', b'MZ'), ('fake.png', b'not a png'), ('x.txt', b'\x00\xff')]:
            with self.subTest(name=name):
                self.assertEqual(self.submit(attachments=SimpleUploadedFile(name, content)).status_code, 200)
                self.assertFalse(Ticket.objects.exists())
        with self.assertRaises(ValidationError):
            validate_uploads([SimpleUploadedFile('a.txt', b'a') for _ in range(6)])
        with override_settings(HELPDESK_MAX_FILE_SIZE=2):
            with self.assertRaises(ValidationError):
                validate_uploads([SimpleUploadedFile('a.txt', b'abc')])
        with self.assertLogs('helpdesk.views', level='ERROR'), patch.object(TicketAttachment, 'save', side_effect=OSError('disk failure')):
            response = self.submit(attachments=SimpleUploadedFile('notes.txt', b'hello'))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Ticket.objects.exists())
        self.assertEqual([p for p in Path(self.media.name).rglob('*') if p.is_file()], [])

    def test_login_csrf_and_logout(self):
        self.client.logout()
        self.assertEqual(self.client.get(reverse('helpdesk:index')).status_code, 302)
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.employee)
        self.assertEqual(csrf_client.post(reverse('helpdesk:create', args=[self.kind.pk]), self.payload()).status_code, 403)
        self.assertEqual(self.client.get(reverse('logout')).status_code, 405)

    def test_reports_permissions_filter_counts_and_local_dates(self):
        ticket = self.ticket()
        Ticket.objects.filter(pk=ticket.pk).update(created_at=datetime(2026, 9, 23, 2, tzinfo=ZoneInfo('UTC')))
        url = reverse('admin:helpdesk_ticket_reports')
        self.client.force_login(self.staff)
        self.assertEqual(self.client.get(url).status_code, 403)
        self.staff.user_permissions.add(*Permission.objects.filter(codename__in=['view_ticket', 'view_reports'], content_type__app_label='helpdesk'))
        response = self.client.get(url, {'created_from': '2026-09-22', 'created_to': '2026-09-22'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['totals'], {'total': 1, 'open': 1, 'unassigned': 1, 'finished': 0})
        self.assertEqual(self.client.get(url, {'created_from': '2026-09-23'}).context['totals']['total'], 0)
        self.assertContains(self.client.get(url, {'created_from': 'bad'}), 'Enter a valid date')

    def test_admin_preview_no_writes_and_field_validation(self):
        url = reverse('admin:helpdesk_tickettype_preview', args=[self.kind.pk])
        self.client.force_login(self.staff)
        self.assertEqual(self.client.get(url).status_code, 403)
        self.client.force_login(self.admin)
        self.assertContains(self.client.get(url), 'Preview')
        self.assertEqual(self.client.post(url, self.payload()).status_code, 405)
        self.assertFalse(Ticket.objects.exists())
        self.field.field_type = 'dropdown'
        self.field.choices = 'Duplicate\nDuplicate'
        with self.assertRaises(ValidationError):
            self.field.full_clean()

    def test_reply_does_not_overwrite_concurrent_staff_changes(self):
        from .services import save_ticket_activity
        ticket = self.ticket()
        Ticket.objects.filter(pk=ticket.pk).update(status='in_progress', assignee=self.admin)
        comment = TicketComment(ticket=ticket, author=self.employee, body='New information')
        save_ticket_activity(ticket, self.employee, [], comment)
        ticket.refresh_from_db()
        self.assertEqual(ticket.status, 'in_progress')
        self.assertEqual(ticket.assignee, self.admin)

    def test_admin_change_with_attachment_only_reply_and_forged_snapshot(self):
        ticket = self.ticket()
        TicketComment.objects.create(ticket=ticket, author=self.employee, body='')
        self.client.force_login(self.admin)
        url = reverse('admin:helpdesk_ticket_change', args=[ticket.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        data = {'status': 'in_progress', 'priority': 'high', 'assignee': self.admin.pk,
                'subject': 'Forged replacement', 'answers': '[]', 'requester': self.other.pk, '_save': 'Save'}
        for inline in response.context['inline_admin_formsets']:
            formset = inline.formset
            data.update({f'{formset.prefix}-TOTAL_FORMS': str(formset.total_form_count()),
                         f'{formset.prefix}-INITIAL_FORMS': str(formset.initial_form_count()),
                         f'{formset.prefix}-MIN_NUM_FORMS': '0', f'{formset.prefix}-MAX_NUM_FORMS': '1000'})
            for index, form in enumerate(formset.initial_forms):
                data[f'{formset.prefix}-{index}-id'] = form.instance.pk
                data[f'{formset.prefix}-{index}-ticket'] = ticket.pk
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302, str(response.context and response.context.get('errors')))
        ticket.refresh_from_db()
        self.assertEqual(ticket.status, 'in_progress')
        self.assertEqual(ticket.assignee, self.admin)
        self.assertEqual(ticket.subject, 'Existing issue')
        self.assertEqual(ticket.requester, self.employee)

    def test_staff_attachment_requires_attachment_permission(self):
        self.submit(attachments=SimpleUploadedFile('notes.txt', b'hello'))
        url = reverse('helpdesk:attachment', args=[TicketAttachment.objects.get().pk])
        self.staff.user_permissions.add(Permission.objects.get(content_type__app_label='helpdesk', codename='view_ticket'))
        self.client.force_login(self.staff)
        self.assertEqual(self.client.get(url).status_code, 404)
        self.staff.user_permissions.add(Permission.objects.get(content_type__app_label='helpdesk', codename='view_ticketattachment'))
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        response.close()

    def test_report_breakdowns_share_filters_and_reject_invalid_ranges(self):
        self.ticket()
        finished = self.ticket()
        finished.status = 'resolved'
        finished.save()
        self.client.force_login(self.admin)
        url = reverse('admin:helpdesk_ticket_reports')
        response = self.client.get(url, {'status': 'resolved', 'category': self.category.pk})
        self.assertEqual(response.context['totals'], {'total': 1, 'open': 0, 'unassigned': 0, 'finished': 1})
        self.assertEqual(sum(x['count'] for x in response.context['by_category']), 1)
        self.assertEqual(sum(x['count'] for x in response.context['by_status']), 1)
        self.assertEqual(response.context['page'].paginator.count, 1)
        response = self.client.get(url, {'created_from': '2026-09-24', 'created_to': '2026-09-22'})
        self.assertContains(response, 'on or before')
        self.assertEqual(response.context['totals']['total'], 0)

    def test_upload_signatures_for_each_supported_document(self):
        from io import BytesIO
        from zipfile import ZipFile
        samples = [('a.png', b'\x89PNG\r\n\x1a\ncontent'), ('a.jpg', b'\xff\xd8\xffcontent'),
                   ('a.pdf', b'%PDF-1.4 content'), ('a.txt', b'notes')]
        for extension, member in [('docx', 'word/document.xml'), ('xlsx', 'xl/workbook.xml')]:
            buffer = BytesIO()
            with ZipFile(buffer, 'w') as archive:
                archive.writestr('[Content_Types].xml', '<Types/>')
                archive.writestr(member, '<document/>')
            samples.append((f'a.{extension}', buffer.getvalue()))
        for name, data in samples:
            with self.subTest(name=name):
                upload = SimpleUploadedFile(name, data)
                self.assertEqual(validate_uploads([upload]), [upload])
                self.assertEqual(upload.tell(), 0)

    def test_malformed_post_empty_reply_and_escaped_answers(self):
        url = reverse('helpdesk:create', args=[self.kind.pk])
        data = self.payload()
        del data['-submit']
        self.assertEqual(self.client.post(url, data).status_code, 400)
        data['-submit'] = ''
        data['-forged'] = ''
        self.assertEqual(self.client.post(url, data).status_code, 400)
        self.submit(**{f'custom_{self.field.pk}': '<script>alert(1)</script>'})
        ticket = Ticket.objects.get()
        url = reverse('helpdesk:detail', args=[ticket.pk])
        self.assertContains(self.client.get(url), '&lt;script&gt;')
        self.assertNotContains(self.client.get(url), '<script>alert(1)</script>')
        self.assertContains(self.client.post(url, {'body': '', '-submit': ''}), 'Enter a reply or attach a file')
        self.assertFalse(ticket.comments.exists())

    def test_partial_storage_write_is_cleaned_up(self):
        from .services import save_ticket_activity
        ticket = self.ticket()
        upload = SimpleUploadedFile('notes.txt', b'original')
        def broken_chunks(*args, **kwargs):
            yield b'partial data'
            raise OSError('interrupted write')
        upload.chunks = broken_chunks
        with self.assertRaises(OSError):
            save_ticket_activity(ticket, self.employee, [upload])
        self.assertFalse(TicketAttachment.objects.exists())
        self.assertEqual([p for p in Path(self.media.name).rglob('*') if p.is_file()], [])

    def test_required_dropdown_starts_blank_and_exposes_required_attribute(self):
        self.field.field_type = 'dropdown'
        self.field.choices = 'One\nTwo'
        self.field.save()
        response = self.client.get(reverse('helpdesk:create', args=[self.kind.pk]))
        self.assertContains(response, '<option value="" selected="selected">Choose an option</option>', html=True)
        self.assertTrue(response.context['form'].fields.subject.input.attrs.required)
        self.assertEqual(self.submit(**{f'custom_{self.field.pk}': ''}).status_code, 200)
        self.assertFalse(Ticket.objects.exists())

    def test_optional_fields_do_not_render_html_required_attribute(self):
        from html.parser import HTMLParser

        class Inputs(HTMLParser):
            def handle_starttag(self, tag, attrs):
                attributes = dict(attrs)
                if tag in ('input', 'textarea', 'select') and attributes.get('name') in ('body', 'attachments'):
                    self.controls.append(attributes)

        for url in (reverse('helpdesk:create', args=[self.kind.pk]),
                    reverse('helpdesk:detail', args=[self.ticket().pk])):
            parser = Inputs()
            parser.controls = []
            parser.feed(self.client.get(url).content.decode())
            self.assertTrue(parser.controls)
            for control in parser.controls:
                self.assertNotIn('required', control)
