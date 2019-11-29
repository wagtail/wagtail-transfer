import json
from unittest import mock

from django.test import TestCase, override_settings
from wagtail.core.models import Page

from tests.models import PageWithRichText, SectionedPage


class TestPagesApi(TestCase):
    fixtures = ['test.json']

    def test_pages_api(self):
        response = self.client.get('/wagtail-transfer/api/pages/2/')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)

        ids_for_import = data['ids_for_import']
        self.assertIn(['wagtailcore.page', 2], ids_for_import)
        self.assertNotIn(['wagtailcore.page', 1], ids_for_import)

        homepage = None
        for obj in data['objects']:
            if obj['model'] == 'tests.simplepage' and obj['pk'] == 2:
                homepage = obj
                break

        self.assertTrue(homepage)
        self.assertEqual(homepage['parent_id'], 1)
        self.assertEqual(homepage['fields']['intro'], "This is the homepage")

        mappings = data['mappings']
        self.assertIn(['wagtailcore.page', 2, "22222222-2222-2222-2222-222222222222"], mappings)
        self.assertIn(['tests.advert', 1, "adadadad-1111-1111-1111-111111111111"], mappings)

    def test_export_root(self):
        response = self.client.get('/wagtail-transfer/api/pages/1/')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)

        root_page = None
        for obj in data['objects']:
            if obj['model'] == 'wagtailcore.page' and obj['pk'] == 1:
                root_page = obj
                break

        self.assertTrue(root_page)
        self.assertEqual(root_page['parent_id'], None)

    def test_parental_keys(self):
        page = SectionedPage(title='How to make a cake', intro="Here is how to make a cake.")
        page.sections.create(title="Create the universe", body="First, create the universe")
        page.sections.create(title="Find some eggs", body="Next, find some eggs")

        parent_page = Page.objects.get(url_path='/home/existing-child-page/')
        parent_page.add_child(instance=page)

        response = self.client.get('/wagtail-transfer/api/pages/%d/' % parent_page.id)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)

        page_data = None
        for obj in data['objects']:
            if obj['model'] == 'tests.sectionedpage' and obj['pk'] == page.pk:
                page_data = obj
                break

        self.assertEqual(len(page_data['fields']['sections']), 2)
        self.assertEqual(page_data['fields']['sections'][0]['model'], 'tests.sectionedpagesection')
        self.assertEqual(page_data['fields']['sections'][0]['fields']['title'], "Create the universe")
        section_id = page_data['fields']['sections'][0]['pk']

        # there should also be a uid mapping for the section
        matching_uids = [
            uid for model_name, pk, uid in data['mappings']
            if model_name == 'tests.sectionedpagesection' and pk == section_id
        ]
        self.assertEqual(len(matching_uids), 1)

    def test_rich_text_with_page_link(self):
        page = PageWithRichText(title="You won't believe how rich this cake was!", body='<p>But I have a <a id="1" linktype="page">link</a></p>')

        parent_page = Page.objects.get(url_path='/home/existing-child-page/')
        parent_page.add_child(instance=page)

        response = self.client.get('/wagtail-transfer/api/pages/%d/' % page.id)

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)

        self.assertIn(['wagtailcore.page', 1, '11111111-1111-1111-1111-111111111111'], data['mappings'])


@override_settings(
    WAGTAILTRANSFER_SOURCES={
        'staging': {
            'BASE_URL': 'https://www.example.com/wagtail-transfer/',
        }
    }
)
@mock.patch('requests.get')
class TestChooserProxyApi(TestCase):
    fixtures = ['test.json']

    def setUp(self):
        self.client.login(username='admin', password='password')

    def test(self, get):
        get.return_value.status_code = 200
        get.return_value.content = b'test content'

        response = self.client.get('/admin/wagtail-transfer/api/chooser-proxy/staging/foo?bar=baz', HTTP_ACCEPT='application/json')

        get.assert_called_once_with('https://www.example.com/wagtail-transfer/api/chooser/pages/foo?bar=baz', headers={'Accept': 'application/json'}, timeout=5)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b'test content')

    def test_with_unknown_source(self, get):
        get.return_value.status_code = 200
        get.return_value.content = b'test content'

        response = self.client.get('/admin/wagtail-transfer/api/chooser-proxy/production/foo?bar=baz', HTTP_ACCEPT='application/json')

        get.assert_not_called()

        self.assertEqual(response.status_code, 404)
