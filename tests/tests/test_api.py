import json
import uuid
from unittest import mock

from django.contrib.contenttypes.models import ContentType
from django.test import TestCase
from wagtail.core.models import Page, Collection

from wagtail_transfer.auth import digest_for_source
from wagtail_transfer.models import IDMapping
from tests.models import Advert, PageWithRichText, SectionedPage, PageWithStreamField, PageWithParentalManyToMany


class TestPagesApi(TestCase):
    fixtures = ['test.json']

    def get(self, page_id):
        digest = digest_for_source('local', str(page_id))
        return self.client.get('/wagtail-transfer/api/pages/%d/?digest=%s' % (page_id, digest))

    def test_incorrect_digest(self):
        response = self.client.get('/wagtail-transfer/api/pages/2/?digest=12345678')
        self.assertEqual(response.status_code, 403)

    def test_pages_api(self):
        response = self.get(2)
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
        response = self.get(1)
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

        response = self.get(parent_page.id)
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

        response = self.get(page.id)

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)

        self.assertIn(['wagtailcore.page', 1, '11111111-1111-1111-1111-111111111111'], data['mappings'])

    def test_streamfield_with_page_links(self):
        # Check that page links in a complex nested StreamField - with StreamBlock, StructBlock, and ListBlock -
        # are all picked up in mappings

        page = PageWithStreamField(title="I have a streamfield",
                                   body=json.dumps([{'type': 'link_block',
                                          'value':
                                              {'page': 1,
                                               'text': 'Test'},
                                          'id': 'fc3b0d3d-d316-4271-9e31-84919558188a'},
                                         {'type': 'page',
                                          'value': 2,
                                          'id': 'c6d07d3a-72d4-445e-8fa5-b34107291176'},
                                         {'type': 'stream',
                                          'value':
                                              [{'type': 'page',
                                                'value': 3,
                                                'id': '8c0d7de7-4f77-4477-be67-7d990d0bfb82'}],
                                          'id': '21ffe52a-c0fc-4ecc-92f1-17b356c9cc94'},
                                         {'type': 'list_of_pages',
                                          'value': [5],
                                          'id': '17b972cb-a952-4940-87e2-e4eb00703997'}]))
        parent_page = Page.objects.get(url_path='/home/existing-child-page/')
        parent_page.add_child(instance=page)

        digest = digest_for_source('local', str(page.id))
        response = self.client.get('/wagtail-transfer/api/pages/%d/?digest=%s' % (page.id, digest))

        data = json.loads(response.content)

        # test PageChooserBlock in StructBlock
        self.assertIn(['wagtailcore.page', 1, '11111111-1111-1111-1111-111111111111'], data['mappings'])
        # test un-nested PageChooserBlock
        self.assertIn(['wagtailcore.page', 2, "22222222-2222-2222-2222-222222222222"], data['mappings'])
        # test PageChooserBlock in StreamBlock
        self.assertIn(['wagtailcore.page', 3, "33333333-3333-3333-3333-333333333333"], data['mappings'])
        # test PageChooserBlock in ListBlock
        self.assertIn(['wagtailcore.page', 5, "00017017-5555-5555-5555-555555555555"], data['mappings'])


    def test_streamfield_with_rich_text(self):
        # Check that page references within a RichTextBlock in StreamField are found correctly

        page = PageWithStreamField(title="My streamfield rich text block has a link",
                                   body=json.dumps([{'type': 'rich_text',
                                          'value': '<p>I link to a <a id="1" linktype="page">page</a>.</p>',
                                          'id': '7d4ee3d4-9213-4319-b984-45be4ded8853'}]))

        parent_page = Page.objects.get(url_path='/home/existing-child-page/')
        parent_page.add_child(instance=page)

        digest = digest_for_source('local', str(page.id))
        response = self.client.get('/wagtail-transfer/api/pages/%d/?digest=%s' % (page.id, digest))

        data = json.loads(response.content)

        self.assertIn(['wagtailcore.page', 1, '11111111-1111-1111-1111-111111111111'], data['mappings'])


    def test_parental_many_to_many(self):

        page = PageWithParentalManyToMany(title="This page has lots of ads!")
        advert_1 = Advert.objects.create(slogan="Buy a thing you definitely need!")
        advert_2 = Advert.objects.create(slogan="Buy a full-scale authentically hydrogen-filled replica of the Hindenburg!")
        page.ads = [advert_1, advert_2]

        parent_page = Page.objects.get(url_path='/home/existing-child-page/')
        parent_page.add_child(instance=page)

        digest = digest_for_source('local', str(page.id))
        response = self.client.get('/wagtail-transfer/api/pages/%d/?digest=%s' % (page.id, digest))

        data = json.loads(response.content)


class TestObjectsApi(TestCase):
    fixtures = ['test.json']

    def test_incorrect_digest(self):
        request_body = json.dumps({
            'tests.advert': [1]
        })

        response = self.client.post(
            '/wagtail-transfer/api/objects/?digest=12345678', request_body, content_type='application/json'
        )
        self.assertEqual(response.status_code, 403)

    def test_objects_api(self):
        request_body = json.dumps({
            'tests.advert': [1]
        })
        digest = digest_for_source('local', request_body)

        response = self.client.post(
            '/wagtail-transfer/api/objects/?digest=%s' % digest, request_body, content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)

        self.assertEqual(data['ids_for_import'], [])
        self.assertEqual(data['objects'][0]['model'], 'tests.advert')
        self.assertEqual(data['objects'][0]['fields']['slogan'], "put a tiger in your tank")

        self.assertEqual(data['mappings'], [['tests.advert', 1, 'adadadad-1111-1111-1111-111111111111']])

    def test_objects_api_with_tree_model(self):
        collection = Collection.objects.get().add_child(instance=Collection(name="Test collection"))
        collection_uid = uuid.uuid4()

        IDMapping.objects.create(
            content_type=ContentType.objects.get_for_model(Collection),
            local_id=collection.id,
            uid=collection_uid,
        )

        request_body = json.dumps({
            'wagtailcore.collection': [collection.id]
        })
        digest = digest_for_source('local', request_body)

        response = self.client.post(
            '/wagtail-transfer/api/objects/?digest=%s' % digest, request_body, content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)

        self.assertEqual(data['ids_for_import'], [])
        self.assertEqual(data['objects'][0]['model'], 'wagtailcore.collection')
        self.assertEqual(data['objects'][0]['fields']['name'], "Test collection")

        self.assertEqual(data['mappings'], [['wagtailcore.collection', collection.id, str(collection_uid)]])


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
