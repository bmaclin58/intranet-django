"""Run with: .venv/Scripts/python.exe manage.py test CalCloud."""
import json
from collections import Counter

from django.contrib.staticfiles import finders
from django.test import SimpleTestCase, override_settings


@override_settings(STORAGES={
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
})
class PortalTests(SimpleTestCase):
    def test_portal_pages_are_public_without_database_access(self):
        for path, title in (
            ('', 'Asset Health'), ('assets/', 'Asset Health Report'),
            ('asset-tracker/', 'What is Asset Tracker?'),
            ('asset-tracker/list/', 'Find / View Asset Tracking Records'),
            ('recalls/', 'Recalls'), ('help/', 'Help and Support'),
            ('changelog/', 'Asset Change Log'),
        ):
            with self.subTest(path=path):
                response = self.client.get('/calcloud/' + path)
                self.assertEqual(response.status_code, 200)
                self.assertContains(response, title)
                self.assertContains(response, 'Local demo')
        self.assertRedirects(self.client.get('/'), '/helpdesk/', fetch_redirect_response=False)

    def test_demo_totals_identifiers_dates_and_relationships(self):
        response = self.client.get('/calcloud/assets/')
        self.assertEqual(response.status_code, 200)
        assets = response.context['payload']['assets']
        self.assertEqual(len(assets), 1590)
        self.assertEqual(sum(row['active'] for row in assets), 782)
        counts = Counter(row['status'] for row in assets if row['active'])
        self.assertEqual({key: counts[key] for key in ('Current', 'Due', 'Overdue', 'In Process')},
                         {'Current': 32, 'Due': 14, 'Overdue': 278, 'In Process': 22})
        barcodes = {row['barcode'] for row in assets}
        self.assertEqual(len(barcodes), 1590)
        self.assertTrue(all(isinstance(row['asset_id'], str) for row in assets))
        self.assertEqual(assets[0]['barcode'], '2107444')
        tracking = self.client.get('/calcloud/asset-tracker/list/').context['payload']['rows']
        self.assertEqual(len(tracking), 28)
        self.assertEqual(tracking[0]['record_id'], '67385')
        self.assertTrue(all(set(row['barcodes']) <= barcodes for row in tracking))
        changes = self.client.get('/calcloud/changelog/').context['payload']['rows']
        self.assertEqual(len(changes), 712)
        self.assertTrue(all(row['barcode'] in barcodes for row in changes))
        recalls = self.client.get('/calcloud/recalls/').context['payload']['rows']
        self.assertEqual(len(recalls), 292)

    def test_tracking_detail_and_missing_record(self):
        response = self.client.get('/calcloud/asset-tracker/67385/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Power Plant')
        self.assertContains(response, '67385')
        self.assertEqual(self.client.get('/calcloud/asset-tracker/999999/').status_code, 404)

    def test_browser_payload_and_local_dependencies(self):
        response = self.client.get('/calcloud/assets/')
        self.assertEqual(response.status_code, 200)
        html = response.content.decode()
        raw = html.split('<script id="portal-data" type="application/json">')[1].split('</script>')[0]
        self.assertEqual(len(json.loads(raw)['assets']), 1590)
        for path in ('CalCloud/portal.css', 'CalCloud/portal.js',
                     'CalCloud/vendor/ag-grid-community-36.2.0.min.js',
                     'CalCloud/logo.png', 'unfold/js/chart/chart.js', 'helpdesk/Lato-Regular.ttf'):
            with self.subTest(path=path):
                self.assertIsNotNone(finders.find(path))
