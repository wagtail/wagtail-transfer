import json
from datetime import date, datetime, timezone
from unittest import mock

from django.contrib.auth.models import AnonymousUser, Group, Permission, User
from django.contrib.contenttypes.models import ContentType
from django.shortcuts import redirect
from django.test import TestCase
from django.urls import reverse

from tests.models import SponsoredPage
from wagtail_transfer.models import IDMapping


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
                        "intro": "This is the updated homepage",
                        "comments": []
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
                        "categories": [],
                        "comments": []
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
                        "categories": [],
                        "comments": []
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
                        "slogan": "put a leopard in your tank",
                        "run_until": "2020-12-23T01:23:45Z",
                        "run_from": "2020-01-21"
                    }
                },
                {
                    "model": "tests.advert",
                    "pk": 8,
                    "fields": {
                        "slogan": "go to work on an egg",
                        "run_until": "2020-01-23T01:23:45Z",
                        "run_from": null
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
        self.assertEqual(updated_page.advert.run_until, datetime(2020, 12, 23, 1, 23, 45, tzinfo=timezone.utc))
        self.assertEqual(updated_page.advert.run_from, date(2020, 1, 21))

        created_page = SponsoredPage.objects.get(url_path='/home/eggs-are-great-too/')
        self.assertEqual(created_page.intro, "you can make cakes with them")
        self.assertEqual(created_page.advert.slogan, "go to work on an egg")
        self.assertEqual(created_page.advert.run_until, datetime(2020, 1, 23, 1, 23, 45, tzinfo=timezone.utc))
        self.assertEqual(created_page.advert.run_from, None)

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
                        "intro": "This is the updated homepage",
                        "comments": []
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
                        "categories": [],
                        "comments": []
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
                        "categories": [],
                        "comments": []
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
                        "slogan": "put a leopard in your tank",
                        "run_until": "2020-12-23T01:23:45Z",
                        "run_from": null
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
        self.assertEqual(updated_page.advert.run_until, datetime(2020, 12, 23, 1, 23, 45, tzinfo=timezone.utc))
        self.assertEqual(updated_page.advert.run_from, None)

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
        self.assertEqual(snippet['model_label'], 'tests.category')
        self.assertEqual(snippet['name'], 'Category')


class ImportPermissionsTests(TestCase):
    fixtures = ["test.json"]

    def setUp(self):
        idmapping_content_type = ContentType.objects.get_for_model(IDMapping)
        can_import_permission = Permission.objects.get(
            content_type=idmapping_content_type, codename="wagtailtransfer_can_import",
        )
        can_access_admin_permission = Permission.objects.get(
            content_type=ContentType.objects.get(
                app_label="wagtailadmin", model="admin",
            ),
            codename="access_admin",
        )

        page_importers_group = Group.objects.create(name="Page importers")
        page_importers_group.permissions.add(can_import_permission)
        page_importers_group.permissions.add(can_access_admin_permission)

        editors = Group.objects.get(name="Editors")

        self.superuser = User.objects.create_superuser(
            username="superuser", email="superuser@example.com", password="password",
        )
        self.inactive_superuser = User.objects.create_superuser(
            username="inactivesuperuser",
            email="inactivesuperuser@example.com",
            password="password",
        )
        self.inactive_superuser.is_active = False
        self.inactive_superuser.save()

        # a user with can_import_pages permission through the 'Page importers' group
        self.page_importer = User.objects.create_user(
            username="pageimporter",
            email="pageimporter@example.com",
            password="password",
        )
        self.page_importer.groups.add(page_importers_group)
        self.page_importer.groups.add(editors)

        # a user with can_import_pages permission through user_permissions
        self.oneoff_page_importer = User.objects.create_user(
            username="oneoffpageimporter",
            email="oneoffpageimporter@example.com",
            password="password",
        )
        self.oneoff_page_importer.user_permissions.add(can_import_permission)
        self.oneoff_page_importer.user_permissions.add(can_access_admin_permission)
        self.oneoff_page_importer.groups.add(editors)

        # a user with can_import_pages permission through user_permissions
        self.vanilla_user = User.objects.create_user(
            username="vanillauser", email="vanillauser@example.com", password="password"
        )
        self.vanilla_user.user_permissions.add(can_access_admin_permission)

        # a user that has can_import_pages permission, but is inactive
        self.inactive_page_importer = User.objects.create_user(
            username="inactivepageimporter",
            email="inactivepageimporter@example.com",
            password="password",
        )
        self.inactive_page_importer.groups.add(page_importers_group)
        self.inactive_page_importer.groups.add(editors)
        self.inactive_page_importer.is_active = False
        self.inactive_page_importer.save()

        self.anonymous_user = AnonymousUser()

        self.permitted_users = [
            self.superuser,
            self.page_importer,
            self.oneoff_page_importer,
        ]
        self.denied_users = [
            self.anonymous_user,
            self.inactive_superuser,
            self.inactive_page_importer,
            self.vanilla_user,
        ]

    def _test_view(self, method, url, data=None, success_url=None):

        for user in self.permitted_users:
            with self.subTest(user=user):
                self.client.login(username=user.username, password="password")
                request = getattr(self.client, method)
                response = request(url, data)
                if success_url:
                    self.assertRedirects(response, success_url)
                else:
                    self.assertEqual(response.status_code, 200)
            self.client.logout()

        for user in self.denied_users:
            with self.subTest(user=user):
                if user.is_authenticated:
                    self.client.login(username=user.username, password="password")

                request = getattr(self.client, method)
                response = request(url, data)
                self.assertEqual(response.status_code, 302)
                if user == self.vanilla_user:
                    # expect redirect loop; cf. https://github.com/wagtail/wagtail/issues/431
                    self.assertEqual(response.status_code, 302)
                    self.assertEqual(
                        response.url, reverse("wagtailadmin_login") + f"?next={url}"
                    )
                else:
                    self.assertRedirects(
                        response, reverse("wagtailadmin_login") + f"?next={url}"
                    )
            self.client.logout()

    def test_chooser_view(self):
        url = "/admin/wagtail-transfer/choose/"
        method = "get"
        self._test_view(method, url)

    @mock.patch("wagtail_transfer.views.import_page")
    def test_do_import_view(self, mock_import_page):
        success_url = "/admin/pages/2/"
        mock_import_page.return_value = redirect(success_url)

        url = "/admin/wagtail-transfer/import/"
        method = "post"
        data = {
            "source": "staging",
            "source_page_id": "12",
            "dest_page_id": "2",
        }
        self._test_view(method, url, data, success_url=success_url)
