from datetime import date

from django.http import Http404
from django.shortcuts import render
from django.urls import reverse

from . import demo_data as demo


NAVIGATION = [
    ('dashboard', 'Dashboard', 'dashboard'), ('assets', 'Assets', 'assets'),
    ('tracker', 'Asset Tracker', 'tracker'), ('recalls', 'Recalls', 'bell'),
    ('help', 'Help And Support', 'support'), ('changelog', 'ChangeLog', 'list'),
]


def field(name, label, kind='text', options=(), advanced=False):
    return {'name': name, 'label': label, 'kind': kind, 'options': options, 'advanced': advanced}


ASSET_FILTERS = [
    field('asset_id', 'Asset ID'), field('barcode', 'Barcode'), field('legacy_barcode', 'Legacy Barcode'),
    field('active', 'Active', 'select', [('','All'), ('yes','Yes'), ('no','No')]),
    field('status', 'Status', 'select', [('', 'Any')] + [(s, s) for s in ('Current','Due','RFS Submitted','In Storage','In Process','No-Date','Overdue')]),
    field('due_date', 'Due Date', 'date'), field('calibration_date', 'Calibration Date', 'date'),
    field('clean_due_date', 'Clean Due Date', 'date'), field('clean_date', 'Clean Date', 'date'),
    field('certificate_number', 'Calibration Certificate Number'), field('description', 'Description'),
    *[field(name, label, advanced=True) for name, label in (
        ('brand','Brand'), ('model','Model Number'), ('serial_number','Serial #'),
        ('location','Location'), ('sub_location','Sub-Location'), ('operating_range','Operating Range'))],
    field('condition', 'Condition', 'select', [('', 'Any')] + [(s,s) for s in ('In Service','Sent for Calibration','Lost','Disposed')], advanced=True),
]
TRACKING_FILTERS = [field(name, label) for name, label in (
    ('asset_ids', 'Asset ID'), ('barcodes', 'Barcode'), ('record_id', 'Record #'),
    ('ticket_number', 'Ticket #'), ('contract', 'Contract #'), ('item_number', 'Item #'), ('paragraph', 'Paragraph'))
] + [field('use_date', 'Use Date', 'date'), field('location', 'Shop/Location', advanced=True)]


def show(request, page, title, template, *, rows=None, assets=None, **context):
    payload = {'page': page, 'health': demo.HEALTH, 'charts': demo.CHARTS,
               'tracker_base': reverse('calcloud:tracker')}
    if rows is not None:
        payload['rows'] = rows
    if assets is not None:
        payload['assets'] = assets
    return render(request, f'CalCloud/{template}.html', {
        'page': page, 'title': title, 'navigation': NAVIGATION,
        'active_nav': 'tracker' if page.startswith('tracking') else page,
        'payload': payload, 'health': demo.HEALTH, 'summary': demo.SUMMARY, **context,
    })


def dashboard(request):
    return show(request, 'dashboard', 'Dashboard', 'dashboard', rows=demo.RECALLS, assets=demo.RECALLS)


def assets(request):
    return show(request, 'assets', 'Assets', 'list', rows=demo.ASSETS, assets=demo.ASSETS,
                filters=ASSET_FILTERS, filter_heading='Filter Your Asset Results Below',
                filter_description='Filter your assets using the options below:', grid_title='Find Your Assets', icon='assets')


def tracker(request):
    return show(request, 'tracker', 'Asset Tracking Records', 'tracker')


def tracking_list(request):
    return show(request, 'tracking_list', 'Asset Tracking', 'list', rows=demo.TRACKING_RECORDS,
                filters=TRACKING_FILTERS, filter_heading='Filter Your Asset Tracking Records',
                filter_description='Filter your asset tracking records using the options below:',
                subtitle='Find / View Asset Tracking Records', grid_title='Find Your Asset Tracking Record', icon='tracker')


def tracking_detail(request, record_id):
    record = demo.TRACKING_BY_ID.get(record_id)
    if record is None:
        raise Http404('Tracking record not found in this demo.')
    instruments = [demo.ASSETS_BY_BARCODE[b] for b in record['barcodes']]
    return show(request, 'tracking_detail', f'Tracking Record #{record_id}', 'tracking_detail',
                rows=instruments, assets=instruments, record=record,
                details=[('Record #', record_id), ('Ticket #', record['ticket_number']),
                         ('Contract #', record['contract']), ('Item #', record['item_number']),
                         ('Paragraph', record['paragraph']), ('Shop/Location', record['location']),
                         ('Use Date', date.fromisoformat(record['use_date']).strftime('%m/%d/%Y'))])


def recalls(request):
    return show(request, 'recalls', 'Recalls', 'list', rows=demo.RECALLS, assets=demo.RECALLS,
                grid_title='Assets in This Table Are Due or Overdue for Service', icon='bell')


def changelog(request):
    barcodes = {row['barcode'] for row in demo.CHANGES}
    return show(request, 'changelog', 'ChangeLog', 'list', rows=demo.CHANGES,
                assets=[demo.ASSETS_BY_BARCODE[b] for b in sorted(barcodes)],
                grid_title='Asset Change Log', icon='list')


def help_support(request):
    return show(request, 'help', 'Help and Support', 'help')
