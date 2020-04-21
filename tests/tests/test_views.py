import json
from unittest import mock

from django.test import TestCase

from wagtail_transfer.operations import ImportPlanner
from tests.models import PageWithRichText, SectionedPage, SimplePage, SponsoredPage


class TestChooseView(TestCase):
    fixtures = ['test.json']

    def setUp(self):
        self.client.login(username='admin', password='password')

    def test_get(self):
        response = self.client.get('/admin/wagtail-transfer/choose/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'data-wagtail-component="content-import-form"')


@mock.patch('requests.post')
@mock.patch('requests.get')
class TestImportView(TestCase):
    fixtures = ['test.json']

    def setUp(self):
        self.client.login(username='admin', password='password')

    def test_run(self, get, post):
        get.return_value.status_code = 200
        get.return_value.content = b"""{
            "ids_for_import": [
                ["wagtailcore.page", 12],
                ["wagtailcore.page", 15],
                ["wagtailcore.page", 16]
            ],
            "mappings": [
                ["wagtailcore.page", 12, "22222222-2222-2222-2222-222222222222"],
                ["wagtailcore.page", 15, "00017017-5555-5555-5555-555555555555"],
                ["wagtailcore.page", 16, "00e99e99-6666-6666-6666-666666666666"],
                ["tests.advert", 11, "adadadad-1111-1111-1111-111111111111"],
                ["tests.advert", 8, "adadadad-8888-8888-8888-888888888888"]
            ],
            "objects": [
                {
                    "model": "tests.simplepage",
                    "pk": 12,
                    "parent_id": 1,
                    "fields": {
                        "title": "Home",
                        "show_in_menus": false,
                        "live": true,
                        "slug": "home",
                        "intro": "This is the updated homepage"
                    }
                },
                {
                    "model": "tests.sponsoredpage",
                    "pk": 15,
                    "parent_id": 12,
                    "fields": {
                        "title": "Oil is still great",
                        "show_in_menus": false,
                        "live": true,
                        "slug": "oil-is-still-great",
                        "advert": 11,
                        "intro": "yay fossil fuels and climate change",
                        "categories": []
                    }
                },
                {
                    "model": "tests.sponsoredpage",
                    "pk": 16,
                    "parent_id": 12,
                    "fields": {
                        "title": "Eggs are great too",
                        "show_in_menus": false,
                        "live": true,
                        "slug": "eggs-are-great-too",
                        "advert": 8,
                        "intro": "you can make cakes with them",
                        "categories": []
                    }
                }
            ]
        }"""

        post.return_value.status_code = 200
        post.return_value.content = """{
            "ids_for_import": [
            ],
            "mappings": [
                ["tests.advert", 11, "adadadad-1111-1111-1111-111111111111"],
                ["tests.advert", 8, "adadadad-8888-8888-8888-888888888888"]
            ],
            "objects": [
                {
                    "model": "tests.advert",
                    "pk": 11,
                    "fields": {
                        "slogan": "put a leopard in your tank"
                    }
                },
                {
                    "model": "tests.advert",
                    "pk": 8,
                    "fields": {
                        "slogan": "go to work on an egg"
                    }
                }
            ]
        }"""

        response = self.client.post('/admin/wagtail-transfer/import/', {
            'source': 'staging',
            'source_page_id': '12',
            'dest_page_id': '2',
        })
        self.assertRedirects(response, '/admin/pages/2/')

        # Pages API should be called once, with 12 as the root page
        get.assert_called_once()
        args, kwargs = get.call_args
        self.assertEqual(args[0], 'https://www.example.com/wagtail-transfer/api/pages/12/')
        self.assertIn('digest', kwargs['params'])

        # then the Objects API should be called, requesting adverts with ID 11 and 8
        post.assert_called_once()
        args, kwargs = post.call_args
        self.assertEqual(args[0], 'https://www.example.com/wagtail-transfer/api/objects/')
        self.assertIn('digest', kwargs['params'])
        requested_ids = json.loads(kwargs['data'])['tests.advert']
        self.assertEqual(set(requested_ids), set([8, 11]))

        # Check import results
        updated_page = SponsoredPage.objects.get(url_path='/home/oil-is-still-great/')
        self.assertEqual(updated_page.intro, "yay fossil fuels and climate change")
        self.assertEqual(updated_page.advert.slogan, "put a leopard in your tank")

        created_page = SponsoredPage.objects.get(url_path='/home/eggs-are-great-too/')
        self.assertEqual(created_page.intro, "you can make cakes with them")
        self.assertEqual(created_page.advert.slogan, "go to work on an egg")

    def test_missing_related_object(self, get, post):
        # If an imported object contains references to an object which does not exist at the source
        # (which in practice cannot happen for a ForeignKey, but could happen in rich text or
        # StreamField data), the importer will make an object-API request for it and get back a
        # response that doesn't contain the object. The importer needs to catch this case and not
        # get into an infinite loop of repeating the object-API request.
        get.return_value.status_code = 200
        get.return_value.content = b"""{
            "ids_for_import": [
                ["wagtailcore.page", 12],
                ["wagtailcore.page", 15],
                ["wagtailcore.page", 16]
            ],
            "mappings": [
                ["wagtailcore.page", 12, "22222222-2222-2222-2222-222222222222"],
                ["wagtailcore.page", 15, "00017017-5555-5555-5555-555555555555"],
                ["wagtailcore.page", 16, "00e99e99-6666-6666-6666-666666666666"],
                ["tests.advert", 11, "adadadad-1111-1111-1111-111111111111"],
                ["tests.advert", 8, "adadadad-8888-8888-8888-888888888888"]
            ],
            "objects": [
                {
                    "model": "tests.simplepage",
                    "pk": 12,
                    "parent_id": 1,
                    "fields": {
                        "title": "Home",
                        "show_in_menus": false,
                        "live": true,
                        "slug": "home",
                        "intro": "This is the updated homepage"
                    }
                },
                {
                    "model": "tests.sponsoredpage",
                    "pk": 15,
                    "parent_id": 12,
                    "fields": {
                        "title": "Oil is still great",
                        "show_in_menus": false,
                        "live": true,
                        "slug": "oil-is-still-great",
                        "advert": 11,
                        "intro": "yay fossil fuels and climate change",
                        "categories": []
                    }
                },
                {
                    "model": "tests.sponsoredpage",
                    "pk": 16,
                    "parent_id": 12,
                    "fields": {
                        "title": "Eggs are great too",
                        "show_in_menus": false,
                        "live": true,
                        "slug": "eggs-are-great-too",
                        "advert": 8,
                        "intro": "you can make cakes with them",
                        "categories": []
                    }
                }
            ]
        }"""

        post.return_value.status_code = 200
        post.return_value.content = """{
            "ids_for_import": [
            ],
            "mappings": [
                ["tests.advert", 11, "adadadad-1111-1111-1111-111111111111"]
            ],
            "objects": [
                {
                    "model": "tests.advert",
                    "pk": 11,
                    "fields": {
                        "slogan": "put a leopard in your tank"
                    }
                }
            ]
        }"""

        response = self.client.post('/admin/wagtail-transfer/import/', {
            'source': 'staging',
            'source_page_id': '12',
            'dest_page_id': '2',
        })
        self.assertRedirects(response, '/admin/pages/2/')

        # Pages API should be called once, with 12 as the root page
        get.assert_called_once()
        args, kwargs = get.call_args
        self.assertEqual(args[0], 'https://www.example.com/wagtail-transfer/api/pages/12/')
        self.assertIn('digest', kwargs['params'])

        # then the Objects API should be called, requesting adverts with ID 11 and 8
        post.assert_called_once()
        args, kwargs = post.call_args
        self.assertEqual(args[0], 'https://www.example.com/wagtail-transfer/api/objects/')
        self.assertIn('digest', kwargs['params'])
        requested_ids = json.loads(kwargs['data'])['tests.advert']
        self.assertEqual(set(requested_ids), set([8, 11]))

        # Check import results
        updated_page = SponsoredPage.objects.get(url_path='/home/oil-is-still-great/')
        self.assertEqual(updated_page.intro, "yay fossil fuels and climate change")
        self.assertEqual(updated_page.advert.slogan, "put a leopard in your tank")

        # The egg advert was missing in the object-api response, and the FK on SponsoredPage is
        # nullable, so it should create the egg page without the advert
        created_page = SponsoredPage.objects.get(url_path='/home/eggs-are-great-too/')
        self.assertEqual(created_page.intro, "you can make cakes with them")
        self.assertEqual(created_page.advert, None)

    def test_list_snippet_models(self, get, post):
        # Test the model chooser view.
        response = self.client.get("https://www.example.com/wagtail-transfer/api/chooser/models/?models=True")
        self.assertEqual(response.status_code, 200)

        content = json.loads(response.content.decode("utf-8"))
        self.assertEqual(content['meta']['total_count'], 1)

        snippet = content['items'][0]
        self.assertEqual(snippet['label'], 'tests.category')
        self.assertEqual(snippet['name'], 'Category')
