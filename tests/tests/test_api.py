import json
import os.path
import shutil
import uuid
from unittest import mock

from django.conf import settings
from django.core.files import File
from django.core.files.images import ImageFile
from django.contrib.contenttypes.models import ContentType
from django.test import TestCase, override_settings
from wagtail.core.models import Page, Collection
from wagtail.images.models import Image
from wagtail.documents.models import Document

from wagtail_transfer.auth import digest_for_source
from wagtail_transfer.models import IDMapping
from tests.models import (
    Advert, Avatar, Category, ModelWithManyToMany, PageWithRichText, SectionedPage, SponsoredPage,
    PageWithStreamField, PageWithParentalManyToMany
)


# We could use settings.MEDIA_ROOT here, but this way we avoid clobbering a real media folder if we
# ever run these tests with non-test settings for any reason
TEST_MEDIA_DIR = os.path.join(os.path.join(settings.BASE_DIR, 'test-media'))
FIXTURES_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'fixtures')


class TestModelsApi(TestCase):
    fixtures = ['test.json']

    def test_model_chooser_response(self):
        response = self.client.get('/wagtail-transfer/api/chooser/models/')
        self.assertEqual(response.status_code, 200)

        content = json.loads(response.content.decode("utf-8"))
        self.assertEqual(content['meta']['total_count'], 1)

        snippet = content['items'][0]
        self.assertEqual(snippet['label'], 'tests.category')
        self.assertEqual(snippet['name'], 'Category')


    def test_model_object_chooser(self):
        response = self.client.get('/wagtail-transfer/api/chooser/models/tests.category/')
        self.assertEqual(response.status_code, 200)

        content = json.loads(response.content.decode("utf-8"))
        self.assertEqual(content['meta']['total_count'], 1)
        self.assertEqual(content['meta']['next'], None)
        self.assertEqual(content['meta']['previous'], None)

        snippet = content['items'][0]
        self.assertEqual(snippet['label'], 'tests.category')
        self.assertEqual(snippet['object_name'], 'red Cars')
        self.assertEqual(snippet['name'], 'Cars')
        self.assertEqual(snippet['colour'], 'red')

    def test_model_object_next_pagination(self):
        # Create 50 more categories
        for i in range(50):
            name = "Car #{}".format(i)
            Category.objects.create(name=name, colour="Violet")

        response = self.client.get('/wagtail-transfer/api/chooser/models/tests.category/')
        self.assertEqual(response.status_code, 200)

        content = json.loads(response.content.decode("utf-8"))
        self.assertEqual(content['meta']['total_count'], 51)
        self.assertTrue(bool(content['meta']['next']))
        self.assertFalse(bool(content['meta']['previous']))

        items = content['items']
        self.assertEqual(len(items), 20)

        # Remove the newly created categories
        Category.objects.filter(colour="Violet").delete()

    def test_model_object_previous_and_next_pagination(self):
        # Create 50 more categories
        for i in range(50):
            name = "Car #{}".format(i)
            Category.objects.create(name=name, colour="Violet")

        response = self.client.get('/wagtail-transfer/api/chooser/models/tests.category/?page=2')
        self.assertEqual(response.status_code, 200)

        content = json.loads(response.content.decode("utf-8"))
        self.assertEqual(content['meta']['total_count'], 51)
        self.assertTrue(bool(content['meta']['previous']))
        self.assertTrue(bool(content['meta']['next']))

        items = content['items']
        self.assertEqual(len(items), 20)

        # Remove the newly created categories
        Category.objects.filter(colour="Violet").delete()

    def test_model_object_previous_pagination(self):
        # Create 50 more categories
        for i in range(50):
            name = "Car #{}".format(i)
            Category.objects.create(name=name, colour="Violet")

        response = self.client.get('/wagtail-transfer/api/chooser/models/tests.category/?page=3')
        self.assertEqual(response.status_code, 200)

        content = json.loads(response.content.decode("utf-8"))
        self.assertEqual(content['meta']['total_count'], 51)
        self.assertTrue(bool(content['meta']['previous']))
        self.assertFalse(bool(content['meta']['next']))

        # Pagination happens 20 at a time by default.
        # Page 3 = 2 pages of 20, with 11 remaining.
        items = content['items']
        self.assertEqual(len(items), 11)

        # Remove the newly created categories
        Category.objects.filter(colour="Violet").delete()


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

    def test_rich_text_with_dead_page_link(self):
        page = PageWithRichText(title="You won't believe how rich this cake was!", body='<p>But I have a <a id="999" linktype="page">link</a></p>')

        parent_page = Page.objects.get(url_path='/home/existing-child-page/')
        parent_page.add_child(instance=page)

        response = self.get(page.id)

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)

        self.assertTrue(any(
            model == 'wagtailcore.page' and id == 999
            for model, id, uid in data['mappings']
        ))

    def test_null_rich_text(self):
        page = PageWithRichText(title="I'm lost for words", body=None)

        parent_page = Page.objects.get(url_path='/home/existing-child-page/')
        parent_page.add_child(instance=page)

        response = self.get(page.id)

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)

        self.assertTrue(any(
            obj['pk'] == page.pk
            for obj in data['objects']
        ))

    def test_rich_text_with_image_embed(self):
        with open(os.path.join(FIXTURES_DIR, 'wagtail.jpg'), 'rb') as f:
            image = Image.objects.create(
                title="Wagtail",
                file=ImageFile(f, name='wagtail.jpg')
            )

        body = '<p>Here is an image</p><embed embedtype="image" id="%d" alt="A wagtail" format="left" />' % image.pk
        page = PageWithRichText(title="The cake is a lie.", body=body)

        parent_page = Page.objects.get(url_path='/home/existing-child-page/')
        parent_page.add_child(instance=page)

        response = self.get(page.id)

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)

        self.assertTrue(any(
            model == 'wagtailimages.image' and pk == image.pk
            for model, pk, uid in data['mappings']
        ))

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

    def test_streamfield_with_dead_page_link(self):
        page = PageWithStreamField(
            title="I have a streamfield",
            body=json.dumps([
                {'type': 'link_block', 'value': {'page': 999, 'text': 'Test'}, 'id': 'fc3b0d3d-d316-4271-9e31-84919558188a'},
            ])
        )
        parent_page = Page.objects.get(url_path='/home/existing-child-page/')
        parent_page.add_child(instance=page)

        digest = digest_for_source('local', str(page.id))
        response = self.client.get('/wagtail-transfer/api/pages/%d/?digest=%s' % (page.id, digest))

        data = json.loads(response.content)
        self.assertTrue(any(
            model == 'wagtailcore.page' and id == 999
            for model, id, uid in data['mappings']
        ))

    def test_streamfield_with_null_page(self):
        # We should gracefully handle null values in non-required chooser blocks
        page = PageWithStreamField(
            title="I have a streamfield",
            body=json.dumps([{
                'type': 'link_block',
                'value': {'page': None, 'text': 'Empty test'},
                'id': 'fc3b0d3d-d316-4271-9e31-84919558188a'
            },])
        )
        parent_page = Page.objects.get(url_path='/home/existing-child-page/')
        parent_page.add_child(instance=page)

        digest = digest_for_source('local', str(page.id))
        response = self.client.get('/wagtail-transfer/api/pages/%d/?digest=%s' % (page.id, digest))

        data = json.loads(response.content)
        # result should have a mapping for the page we just created, and its parent
        self.assertEqual(len(data['mappings']), 2)

    def test_parental_many_to_many(self):
        page = PageWithParentalManyToMany(title="This page has lots of ads!")
        advert_2 = Advert.objects.get(id=2)
        advert_3 = Advert.objects.get(id=3)
        page.ads = [advert_2, advert_3]

        parent_page = Page.objects.get(url_path='/home/existing-child-page/')
        parent_page.add_child(instance=page)

        digest = digest_for_source('local', str(page.id))
        response = self.client.get('/wagtail-transfer/api/pages/%d/?digest=%s' % (page.id, digest))

        data = json.loads(response.content)

        self.assertIn(['tests.advert', 2, "adadadad-2222-2222-2222-222222222222"], data['mappings'])
        self.assertIn(['tests.advert', 3, "adadadad-3333-3333-3333-333333333333"], data['mappings'])
        self.assertEqual({2, 3}, set(data['objects'][0]['fields']['ads']))

    def test_related_model_with_field_lookup(self):
        page = SponsoredPage.objects.get(id=5)
        page.categories.add(Category.objects.get(name='Cars'))
        page.save()

        response = self.get(5)
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)

        mappings = data['mappings']

        # Category objects in the mappings section should be identified by name, not UUID
        self.assertIn(['tests.category', 1, ['Cars']], mappings)


class TestObjectsApi(TestCase):
    fixtures = ['test.json']

    def setUp(self):
        shutil.rmtree(TEST_MEDIA_DIR, ignore_errors=True)

    def tearDown(self):
        shutil.rmtree(TEST_MEDIA_DIR, ignore_errors=True)

    def test_incorrect_digest(self):
        request_body = json.dumps({
            'tests.advert': [1]
        })

        response = self.client.post(
            '/wagtail-transfer/api/objects/?digest=12345678', request_body, content_type='application/json'
        )
        self.assertEqual(response.status_code, 403)

    def get(self, request_body):
        request_json = json.dumps(request_body)
        digest = digest_for_source('local', request_json)
        return self.client.post(
            '/wagtail-transfer/api/objects/?digest=%s' % digest, request_json, content_type='application/json'
        )

    def test_objects_api(self):
        response = self.get({
            'tests.advert': [1]
        })
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)

        self.assertEqual(data['ids_for_import'], [])
        self.assertEqual(data['objects'][0]['model'], 'tests.advert')
        self.assertEqual(data['objects'][0]['fields']['slogan'], "put a tiger in your tank")

        self.assertEqual(data['mappings'], [['tests.advert', 1, 'adadadad-1111-1111-1111-111111111111']])

    def test_objects_api_with_tree_model(self):
        root_collection = Collection.objects.get()
        collection = root_collection.add_child(instance=Collection(name="Test collection"))
        collection_uid = uuid.uuid4()

        collection_content_type = ContentType.objects.get_for_model(Collection)

        IDMapping.objects.create(
            content_type=collection_content_type,
            local_id=collection.id,
            uid=collection_uid,
        )

        response = self.get({
            'wagtailcore.collection': [collection.id]
        })
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)

        self.assertEqual(data['ids_for_import'], [])
        self.assertEqual(data['objects'][0]['model'], 'wagtailcore.collection')
        self.assertEqual(data['objects'][0]['fields']['name'], "Test collection")

        # mappings should contain entries for the requested collection and its parent
        self.assertIn(
            ['wagtailcore.collection', collection.id, str(collection_uid)],
            data['mappings']
        )
        root_collection_uid = IDMapping.objects.get(
            content_type=collection_content_type, local_id=root_collection.id
        ).uid
        self.assertIn(
            ['wagtailcore.collection', root_collection.id, str(root_collection_uid)],
            data['mappings']
        )

    def test_many_to_many(self):
        advert_2 = Advert.objects.get(id=2)
        advert_3 = Advert.objects.get(id=3)
        ad_holder = ModelWithManyToMany.objects.create()
        ad_holder.ads.set([advert_2, advert_3])
        ad_holder.save()

        response = self.get({
            'tests.modelwithmanytomany': [1]
        })
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)

        self.assertIn(['tests.advert', 2, "adadadad-2222-2222-2222-222222222222"], data['mappings'])
        self.assertIn(['tests.advert', 3, "adadadad-3333-3333-3333-333333333333"], data['mappings'])
        self.assertEqual({2, 3}, set(data['objects'][0]['fields']['ads']))

    def test_model_with_field_lookup(self):
        response = self.get({
            'tests.category': [1]
        })
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)

        # Category objects in the mappings section should be identified by name, not UUID
        self.assertIn(['tests.category', 1, ['Cars']], data['mappings'])

    def test_image(self):
        with open(os.path.join(FIXTURES_DIR, 'wagtail.jpg'), 'rb') as f:
            image = Image.objects.create(
                title="Wagtail",
                file=ImageFile(f, name='wagtail.jpg')
            )

        response = self.get({
            'wagtailimages.image': [image.pk]
        })
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)

        self.assertEqual(len(data['objects']), 1)
        obj = data['objects'][0]
        self.assertEqual(obj['fields']['file']['download_url'], 'http://media.example.com/media/original_images/wagtail.jpg')
        self.assertEqual(obj['fields']['file']['size'], 1160)
        self.assertEqual(obj['fields']['file']['hash'], '45c5db99aea04378498883b008ee07528f5ae416')

    @override_settings(MEDIA_URL='/media/')
    def test_image_with_local_media_url(self):
        """File URLs should use BASE_URL to form an absolute URL if MEDIA_URL is relative"""
        with open(os.path.join(FIXTURES_DIR, 'wagtail.jpg'), 'rb') as f:
            image = Image.objects.create(
                title="Wagtail",
                file=ImageFile(f, name='wagtail.jpg')
            )

        response = self.get({
            'wagtailimages.image': [image.pk]
        })
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)

        self.assertEqual(len(data['objects']), 1)
        obj = data['objects'][0]
        self.assertEqual(obj['fields']['file']['download_url'], 'http://example.com/media/original_images/wagtail.jpg')
        self.assertEqual(obj['fields']['file']['size'], 1160)
        self.assertEqual(obj['fields']['file']['hash'], '45c5db99aea04378498883b008ee07528f5ae416')

    def test_document(self):
        with open(os.path.join(FIXTURES_DIR, 'document.txt'), 'rb') as f:
            document = Document.objects.create(
                title="Test document",
                file=File(f, name='document.txt')
            )

        response = self.get({
            'wagtaildocs.document': [document.pk]
        })
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)

        self.assertEqual(len(data['objects']), 1)
        obj = data['objects'][0]
        self.assertEqual(obj['fields']['file']['download_url'], 'http://media.example.com/media/documents/document.txt')
        self.assertEqual(obj['fields']['file']['size'], 33)
        self.assertEqual(obj['fields']['file']['hash'], '9b90daf19b6e1e8a4852c64f9ea7fec5bcc5f7fb')

    def test_custom_model_with_file_field(self):
        with open(os.path.join(FIXTURES_DIR, 'wagtail.jpg'), 'rb') as f:
            avatar = Avatar.objects.create(
                image=ImageFile(f, name='wagtail.jpg')
            )

        response = self.get({
            'tests.avatar': [avatar.pk]
        })
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)

        self.assertEqual(len(data['objects']), 1)
        obj = data['objects'][0]
        self.assertEqual(obj['fields']['image']['download_url'], 'http://media.example.com/media/avatars/wagtail.jpg')
        self.assertEqual(obj['fields']['image']['size'], 1160)
        self.assertEqual(obj['fields']['image']['hash'], '45c5db99aea04378498883b008ee07528f5ae416')


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
