"""Deterministic demo snapshot; no live CalCloud records or business rules.

The first visible rows reproduce the supplied examples. Other rows, links between
records, and chart history are synthetic. Dates/statuses are frozen for the demo.
"""
from collections import Counter
from datetime import date, timedelta


DESCRIPTIONS = [
    ('DIGITAL MULTIMETER', 'FLUKE CORPORATION', '87V'),
    ('GAUGE PRESSURE 0-160 PSI', 'ASHCROFT', '1009'),
    ('TORQUE WRENCH, 20-150 FT-LB', 'SNAP-ON', 'QD3R150'),
    ('DIGITAL CALIPER, 0-6 IN', 'MITUTOYO', '500-196-30'),
    ('IR THERMOMETER', 'FLUKE CORPORATION', '62 MAX'),
    ('DIAL INDICATOR, 0-0.2 IN', 'STARRETT', '25-111'),
]
LOCATIONS = ['Power Plant', 'Warehouse', 'Paint Shop', 'Drydock', 'Southeast dock', 'Machine Shop']


def make_assets():
    rows = []
    for i in range(1590):
        status = ('Current' if i < 32 else 'Due' if i < 46 else 'Overdue' if i < 324
                  else 'In Process' if i < 346 else 'In Storage' if 346 <= i < 400 else 'No-Date')
        description, brand, model = DESCRIPTIONS[i % len(DESCRIPTIONS)]
        due = (date(2029, 4, 30) if status == 'Current' else
               date(2026, 9, 25) + timedelta(days=i - 32) if status == 'Due' else
               date(2025, 1, 1) + timedelta(days=(i - 46) % 200) if status == 'Overdue' else None)
        rows.append({
            'barcode': str(3000000 + i), 'asset_id': f'DEMO-{i + 1:04d}',
            'legacy_barcode': '' if i % 3 else f'L-{i + 1:05d}',
            'active': i < 782, 'disposition': 'Active' if i < 782 else 'Inactive',
            'status': status, 'due_date': due.isoformat() if due else None,
            'calibration_date': '2024-09-26' if status == 'Current' else '2025-01-27',
            'calibration_interval': '12 months', 'description': description,
            'brand': brand, 'model': model, 'serial_number': f'SN-{100000 + i}',
            'location': LOCATIONS[i % len(LOCATIONS)], 'sub_location': f'Bay {i % 5 + 1}',
            'certificate_number': f'DEMO-CAL-{i + 1:05d}' if i % 4 else '',
            'special_calibration': False, 'clean_date': '2025-01-27' if i % 3 == 0 else None,
            'clean_due_date': '2026-01-27' if i % 3 == 0 else None,
            'operating_range': ['0–1000 V', '0–160 PSI', '20–150 FT-LB', '0–6 IN', '-30–500 °C', '0–0.2 IN'][i % 6],
            'condition': 'Sent for Calibration' if status == 'In Process' else 'In Service' if i < 782 else 'Disposed',
            'notes': 'Synthetic demonstration record.',
        })
    for i, (asset_id, barcode) in enumerate([
        ('1390', '2107444'), ('1392', '2107350'), ('1357', '2107351'), ('1381', '2107388'),
        ('1356', '2107409'), ('1393', '2107441'), ('1382', '2107442'), ('1383', '2107443'),
        ('1358', '2107445'), ('1387', '2107446'),
    ]):
        rows[i].update(asset_id=asset_id, barcode=barcode, legacy_barcode='',
                       due_date='2029-05-31' if i == 0 else '2029-04-30')
    for i, (barcode, due, description) in enumerate([
        ('2007102', '2019-01-09', 'IR THERMOMETER'), ('2007108', '2019-01-09', 'IR THERMOMETER'),
        ('2012512', '2019-04-25', 'GAUGE PRESSURE 0-160 PSI'), ('2017147', '2019-04-25', 'CO MONITOR'),
        ('2002234', '2019-05-01', 'DIAL INDICATOR, 0-0.2 IN'), ('2002377', '2019-06-21', 'OUTSIDE MICROMETER, 0-1 IN'),
        ('2002824', '2019-06-21', 'MEGOHMMETER'), ('2002834', '2019-06-21', 'MEGOHMMETER'),
        ('2002850', '2019-06-23', 'MILLIOHMMETER'), ('2013140', '2019-07-23', 'GAUGE PRESSURE 0-200 PSI'),
    ]):
        rows[46 + i].update(barcode=barcode, asset_id='#1' if i == 9 else '', due_date=due,
                            description=description, calibration_interval='', certificate_number='')
    rows[46].update(brand='FLUKE CORPORATION', model='62 MAX', serial_number='', location='', sub_location='')
    for i, (barcode, asset_id, serial) in enumerate([
        ('2019933', 'DIJR003', ''), ('2009918', 'AMAV001', ''), ('2009084', 'T0049', '700594'),
        ('2010030', 'DC0005', 'E81920'), ('2010391', 'DISH001', '45464'),
        ('2010066', 'DI0003', ''), ('2015056', 'T0032', ''), ('2021519', 'OD0067-1', ''),
    ]):
        rows[782 + i].update(barcode=barcode, asset_id=asset_id, serial_number=serial)
    return rows


ASSETS = make_assets()
ASSETS_BY_BARCODE = {row['barcode']: row for row in ASSETS}
RECALLS = sorted((row for row in ASSETS if row['active'] and row['status'] in ('Due', 'Overdue')),
                 key=lambda row: (row['due_date'], row['barcode']))
STATUS_COUNTS = Counter(row['status'] for row in ASSETS if row['active'])
HEALTH = [{'label': label, 'count': STATUS_COUNTS[label], 'color': color} for label, color in (
    ('Current', '#009b3a'), ('Due', '#dff52e'), ('Overdue', '#cb0000'), ('In Process', '#0ab1ed'))]
SUMMARY = [
    {'label': 'Active', 'count': sum(row['active'] for row in ASSETS), 'query': 'active=yes', 'icon': 'toggle-on'},
    {'label': 'Inactive', 'count': sum(not row['active'] for row in ASSETS), 'query': 'active=no', 'icon': 'toggle-off'},
    {'label': 'Due', 'count': STATUS_COUNTS['Due'], 'query': 'status=Due', 'icon': 'calendar'},
    {'label': 'Overdue', 'count': STATUS_COUNTS['Overdue'], 'query': 'status=Overdue', 'icon': 'warning'},
]


def make_tracking():
    examples = [
        ('67385', '1116', '1.1.1.5', '598', '5-2', 'Power Plant', '2023-03-15'),
        ('68035', '123456', '007', '456', '1', 'Warehouse', '1988-01-20'),
        ('75367', '1127', '1.1.5.7', '4925', '1.23.4', 'Paint Shop', '2023-03-21'),
        ('75384', '90878', '987789', '8.9', '9.8', 'Paint Shop', '2023-03-02'),
        ('98691', '651651', '1.61.8', '5489', '10-10', 'Newport News Shipyard', '2023-04-14'),
        ('98692', '5874', '5.9.6.4', '7891011', '79-1', 'Norfolk Shipyard', '2023-04-04'),
        ('98693', 'sdfgsdfg', 'ASDFG', 'ASDFG', 'ASDFG', 'ARG', '2023-04-05'),
        ('148090', '1112', '1.1.1.2', '1235', '3', 'Drydock', '2023-07-07'),
        ('217481', '1111', '1.1.1.1', '1234', '2', 'Southeast dock', '2024-03-04'),
        ('217638', '', '', '', '', '', '2024-03-07'),
    ]
    for i in range(18):
        examples.append((str(218000 + i), str(1200 + i), f'1.2.{i + 1}', str(4000 + i),
                         str(i + 1), LOCATIONS[i % 6], (date(2024, 4, 1) + timedelta(days=i * 12)).isoformat()))
    rows = []
    for i, values in enumerate(examples):
        record = dict(zip(('record_id', 'ticket_number', 'contract', 'item_number', 'paragraph', 'location', 'use_date'), values))
        instruments = ASSETS[i:i + 2]
        record.update(barcodes=[asset['barcode'] for asset in instruments],
                      asset_ids=[asset['asset_id'] for asset in instruments],
                      notes='Instrument associations are synthetic demo data.')
        rows.append(record)
    return rows


TRACKING_RECORDS = make_tracking()
TRACKING_BY_ID = {row['record_id']: row for row in TRACKING_RECORDS}


def make_changes():
    examples = [
        ('2019933', 'Custom Notes', '', 'Calibrated by MMC - Due Date 9/5/2027'),
        ('2009918', 'Custom Notes', '', 'Calibrated by MMC - Due Date 9/5/2027'),
        ('2009084', 'Active', 'Yes', 'No'), ('2010030', 'Active', 'Yes', 'No'),
        ('2010391', 'Active', 'Yes', 'No'), ('2010066', 'Active', 'Yes', 'No'),
        ('2010066', 'Asset ID', 'D10003', 'DI0003'), ('2015056', 'Active', 'No', 'Yes'),
        ('2015056', 'Active', 'Yes', 'No'), ('2021519', 'Active', 'Yes', 'No'),
    ]
    rows = []
    for i in range(712):
        barcode, field, previous, new = (examples[i] if i < len(examples) else
            (ASSETS[i % 80]['barcode'], 'Location', LOCATIONS[i % 6], LOCATIONS[(i + 1) % 6]))
        asset = ASSETS_BY_BARCODE[barcode]
        rows.append({'id': str(i + 1), 'barcode': barcode, 'asset_id': asset['asset_id'],
                     'serial_number': asset['serial_number'], 'field': field,
                     'previous': previous, 'new': new,
                     'changed_at': (date(2026, 9, 24) - timedelta(days=i // 4)).isoformat(),
                     'changed_by': 'Demo user'})
    return rows


CHANGES = make_changes()
CHARTS = {
    'months': ['Sep 2025', 'Oct 2025', 'Nov 2025', 'Dec 2025', 'Jan 2026', 'Feb 2026', 'Mar 2026', 'Apr 2026', 'May 2026', 'Jun 2026', 'Jul 2026', 'Aug 2026'],
    'services': [
        {'label': 'In Lab', 'data': [83, 0, 0, 0, 3, 2, 29, 4, 2, 12, 11, 113], 'backgroundColor': '#accfba'},
        {'label': 'On Site', 'data': [0, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], 'backgroundColor': '#00983e'},
        {'label': 'Out Of Lab', 'data': [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], 'backgroundColor': '#003c19'},
    ],
    'tolerance': [
        {'label': 'In Tolerance', 'data': [71, 1, 0, 0, 3, 2, 25, 3, 2, 10, 10, 98], 'backgroundColor': '#accfba'},
        {'label': 'Adjusted Into Tolerance', 'data': [10, 0, 0, 0, 0, 0, 3, 1, 0, 2, 1, 12], 'backgroundColor': '#eadba5'},
        {'label': 'Out Of Tolerance', 'data': [3, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 3], 'backgroundColor': '#dba7a7'},
    ],
}
