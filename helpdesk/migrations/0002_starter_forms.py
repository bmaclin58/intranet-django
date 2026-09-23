from django.db import migrations


def seed_forms(apps, schema_editor):
    Category = apps.get_model('helpdesk', 'Category')
    TicketType = apps.get_model('helpdesk', 'TicketType')
    TicketField = apps.get_model('helpdesk', 'TicketField')
    examples = [
        ('Hardware', 'Computers, peripherals, and equipment.', 'Computer problem',
         'Get help with a computer or connected device.', [
             ('Asset tag', 'text', False, ''),
             ('Location', 'dropdown', True, 'On-site\nRemote\nOther'),
             ('Operating system', 'dropdown', False, 'Windows\nmacOS\nLinux\nOther'),
         ]),
        ('Software', 'Applications and software troubleshooting.', 'Software issue',
         'Report a problem with an application.', [
             ('Application name', 'text', True, ''), ('Version', 'text', False, ''),
             ('Error message', 'textarea', False, ''),
         ]),
        ('Access', 'Accounts and access requests.', 'Access request',
         'Ask IT to review access to a system or application.', [
             ('System or application', 'text', True, ''),
             ('Access needed', 'textarea', True, ''), ('Needed by', 'date', False, ''),
         ]),
    ]
    for position, (name, description, type_name, type_description, fields) in enumerate(examples):
        category, _ = Category.objects.get_or_create(name=name, defaults={'description': description, 'position': position})
        kind, created = TicketType.objects.get_or_create(category=category, name=type_name, defaults={'description': type_description})
        if created:
            for index, (label, field_type, required, choices) in enumerate(fields):
                TicketField.objects.create(ticket_type=kind, label=label, field_type=field_type,
                                           required=required, choices=choices, position=index)


class Migration(migrations.Migration):
    dependencies = [('helpdesk', '0001_initial')]
    operations = [migrations.RunPython(seed_forms, migrations.RunPython.noop)]
