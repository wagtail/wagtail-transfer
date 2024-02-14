import importlib
import os.path
import shutil
from datetime import datetime, timezone
from string import Template
from unittest import mock

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.files.images import ImageFile
from django.test import TestCase, override_settings
from wagtail.images.models import Image
from wagtail.models import Collection, Page

from tests.models import (Advert, Author, Avatar, Category, LongAdvert,
                          ModelWithManyToMany, PageWithParentalManyToMany,
                          PageWithRelatedPages, PageWithRichText,
                          PageWithStreamField, RedirectPage, SectionedPage,
                          SimplePage, SponsoredPage)
from wagtail_transfer.models import IDMapping
from wagtail_transfer.operations import ImportPlanner

# We could use settings.MEDIA_ROOT here, but this way we avoid clobbering a real media folder if we
# ever run these tests with non-test settings for any reason
TEST_MEDIA_DIR = os.path.join(os.path.join(settings.BASE_DIR, 'test-media'))
FIXTURES_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'fixtures')

CUSTOM_LINK_TYPE_IDENTIFIERS = ("custom-link-notimplemented", "custom-link-none")

class TestImport(TestCase):
    fixtures = ['test.json']

    def setUp(self):
        shutil.rmtree(TEST_MEDIA_DIR, ignore_errors=True)

    def tearDown(self):
        shutil.rmtree(TEST_MEDIA_DIR, ignore_errors=True)

    def test_import_model(self):
        # Import a Category
        data = """{
            "ids_for_import": [
                ["tests.category", 1]
            ],
            "mappings": [
                ["tests.category", 1, "11111111-1111-1111-1111-111111111111"]
            ],
            "objects": [
                {
                    "model": "tests.category",
                    "pk": 1,
                    "fields": {
                        "name": "Category Test Import",
                        "colour": "red..ish?"
                    }
                }
            ]
        }"""

        importer = ImportPlanner(model="tests.category")
        importer.add_json(data)
        importer.run()

        cats = Category.objects.all()
        self.assertEqual(cats.count(), 2)


    def test_import_pages(self):
        # make a draft edit to the homepage
        home = SimplePage.objects.get(slug='home')
        home.title = "Draft home"
        home.save_revision()

        data = """{
            "ids_for_import": [
                ["wagtailcore.page", 12],
                ["wagtailcore.page", 15]
            ],
            "mappings": [
                ["wagtailcore.page", 12, "22222222-2222-2222-2222-222222222222"],
                ["wagtailcore.page", 15, "55555555-5555-5555-5555-555555555555"]
            ],
            "objects": [
                {
                    "model": "tests.simplepage",
                    "pk": 15,
                    "parent_id": 12,
                    "fields": {
                        "title": "Imported child page",
                        "show_in_menus": false,
                        "live": true,
                        "slug": "imported-child-page",
                        "intro": "This page is imported from the source site",
                        "wagtail_admin_comments": []
                    }
                },
                {
                    "model": "tests.simplepage",
                    "pk": 12,
                    "parent_id": 1,
                    "fields": {
                        "title": "New home",
                        "show_in_menus": false,
                        "live": true,
                        "slug": "home",
                        "intro": "This is the updated homepage",
                        "wagtail_admin_comments": []
                    }
                }
            ]
        }"""

        importer = ImportPlanner(root_page_source_pk=12, destination_parent_id=None)
        importer.add_json(data)
        importer.run()

        updated_page = SimplePage.objects.get(url_path='/home/')
        self.assertEqual(updated_page.intro, "This is the updated homepage")
        self.assertEqual(updated_page.title, "New home")
        self.assertEqual(updated_page.draft_title, "New home")

        # get_latest_revision (as used in the edit-page view) should also reflect the imported content
        updated_page_revision = updated_page.get_latest_revision_as_object()
        self.assertEqual(updated_page_revision.intro, "This is the updated homepage")
        self.assertEqual(updated_page_revision.title, "New home")

        created_page = SimplePage.objects.get(url_path='/home/imported-child-page/')
        self.assertEqual(created_page.intro, "This page is imported from the source site")
        # An initial page revision should also be created
        self.assertTrue(created_page.get_latest_revision())
        created_page_revision = created_page.get_latest_revision_as_object()
        self.assertEqual(created_page_revision.intro, "This page is imported from the source site")

    def test_import_pages_with_fk(self):
        data = """{
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
                ["tests.advert", 8, "adadadad-8888-8888-8888-888888888888"],
                ["tests.author", 100, "b00cb00c-1111-1111-1111-111111111111"]
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
                        "wagtail_admin_comments": []
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
                        "author": 100,
                        "categories": [],
                        "wagtail_admin_comments": []
                    }
                },
                {
                    "model": "tests.advert",
                    "pk": 11,
                    "fields": {
                        "slogan": "put a leopard in your tank",
                        "run_until": "2020-12-23T21:05:43Z",
                        "run_from": null
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
                        "wagtail_admin_comments": []
                    }
                },
                {
                    "model": "tests.advert",
                    "pk": 8,
                    "fields": {
                        "slogan": "go to work on an egg",
                        "run_until": "2020-12-23T01:23:45Z",
                        "run_from": null
                    }
                },
                {
                    "model": "tests.author",
                    "pk": 100,
                    "fields": {
                        "name": "Jack Kerouac",
                        "bio": "Jack Kerouac's car has been fixed now."
                    }
                }
            ]
        }"""

        importer = ImportPlanner(root_page_source_pk=12, destination_parent_id=None)
        importer.add_json(data)
        importer.run()

        updated_page = SponsoredPage.objects.get(url_path='/home/oil-is-still-great/')
        self.assertEqual(updated_page.intro, "yay fossil fuels and climate change")
        # advert is listed in WAGTAILTRANSFER_UPDATE_RELATED_MODELS, so changes to the advert should have been pulled in too
        self.assertEqual(updated_page.advert.slogan, "put a leopard in your tank")
        self.assertEqual(updated_page.advert.run_until, datetime(2020, 12, 23, 21, 5, 43, tzinfo=timezone.utc))
        self.assertEqual(updated_page.advert.run_from, None)
        # author is not listed in WAGTAILTRANSFER_UPDATE_RELATED_MODELS, so should be left unchanged
        self.assertEqual(updated_page.author.bio, "Jack Kerouac's car has broken down.")

        created_page = SponsoredPage.objects.get(url_path='/home/eggs-are-great-too/')
        self.assertEqual(created_page.intro, "you can make cakes with them")
        self.assertEqual(created_page.advert.slogan, "go to work on an egg")
        self.assertEqual(created_page.advert.run_until, datetime(2020, 12, 23, 1, 23, 45, tzinfo=timezone.utc))
        self.assertEqual(created_page.advert.run_from, None)

    def test_import_pages_with_orphaned_uid(self):
        # the author UID listed here exists in the destination's IDMapping table, but
        # the Author record is missing; this would correspond to an author that was previously
        # imported and then deleted.
        data = """{
            "ids_for_import": [
                ["wagtailcore.page", 15]
            ],
            "mappings": [
                ["wagtailcore.page", 15, "00017017-5555-5555-5555-555555555555"],
                ["tests.advert", 11, "adadadad-1111-1111-1111-111111111111"],
                ["tests.author", 100, "b00cb00c-0000-0000-0000-00000de1e7ed"]
            ],
            "objects": [
                {
                    "model": "tests.sponsoredpage",
                    "pk": 15,
                    "parent_id": 1,
                    "fields": {
                        "title": "Oil is still great",
                        "show_in_menus": false,
                        "live": true,
                        "slug": "oil-is-still-great",
                        "advert": 11,
                        "intro": "yay fossil fuels and climate change",
                        "author": 100,
                        "categories": [],
                        "wagtail_admin_comments": []
                    }
                },
                {
                    "model": "tests.advert",
                    "pk": 11,
                    "fields": {
                        "slogan": "put a leopard in your tank",
                        "run_until": "2020-12-23T21:05:43Z",
                        "run_from": null
                    }
                },
                {
                    "model": "tests.author",
                    "pk": 100,
                    "fields": {
                        "name": "Edgar Allen Poe",
                        "bio": "Edgar Allen Poe has come back from the dead"
                    }
                }
            ]
        }"""

        importer = ImportPlanner(root_page_source_pk=15, destination_parent_id=None)
        importer.add_json(data)
        importer.run()

        updated_page = SponsoredPage.objects.get(url_path='/home/oil-is-still-great/')
        # author should be recreated
        self.assertEqual(updated_page.author.name, "Edgar Allen Poe")
        self.assertEqual(updated_page.author.bio, "Edgar Allen Poe has come back from the dead")
        # make sure it has't just overwritten the old author...
        self.assertTrue(Author.objects.filter(name="Jack Kerouac").exists())

        # there should now be an IDMapping record for the previously orphaned UID, pointing to the
        # newly created author
        self.assertEqual(
            IDMapping.objects.get(uid="b00cb00c-0000-0000-0000-00000de1e7ed").content_object,
            updated_page.author
        )

    def test_import_page_with_child_models(self):
        data = """{
            "ids_for_import": [
                ["wagtailcore.page", 100]
            ],
            "mappings": [
                ["wagtailcore.page", 100, "10000000-1000-1000-1000-100000000000"],
                ["tests.sectionedpagesection", 101, "10100000-1010-1010-1010-101000000000"],
                ["tests.sectionedpagesection", 102, "10200000-1020-1020-1020-102000000000"]
            ],
            "objects": [
                {
                    "model": "tests.sectionedpage",
                    "pk": 100,
                    "parent_id": 1,
                    "fields": {
                        "title": "How to boil an egg",
                        "show_in_menus": false,
                        "live": true,
                        "slug": "how-to-boil-an-egg",
                        "intro": "This is how to boil an egg",
                        "sections": [101, 102],
                        "wagtail_admin_comments": []
                    }
                },
                {
                    "model": "tests.sectionedpagesection",
                    "pk": 101,
                    "fields": {
                        "sort_order": 0,
                        "title": "Boil the outside of the egg",
                        "body": "...",
                        "page": 100
                    }
                },
                {
                    "model": "tests.sectionedpagesection",
                    "pk": 102,
                    "fields": {
                        "sort_order": 1,
                        "title": "Boil the rest of the egg",
                        "body": "...",
                        "page": 100
                    }
                }
            ]
        }"""

        importer = ImportPlanner(root_page_source_pk=100, destination_parent_id=2)
        importer.add_json(data)
        importer.run()

        page = SectionedPage.objects.get(url_path='/home/how-to-boil-an-egg/')
        self.assertEqual(page.sections.count(), 2)
        self.assertEqual(page.sections.first().title, "Boil the outside of the egg")

        page_id = page.id
        sections = page.sections.all()
        section_1_id = sections[0].id
        section_2_id = sections[1].id

        # now try re-importing to update the existing page; among the child objects there will be
        # one deletion, one update and one creation

        data = """{
            "ids_for_import": [
                ["wagtailcore.page", 100]
            ],
            "mappings": [
                ["wagtailcore.page", 100, "10000000-1000-1000-1000-100000000000"],
                ["tests.sectionedpagesection", 102, "10200000-1020-1020-1020-102000000000"],
                ["tests.sectionedpagesection", 103, "10300000-1030-1030-1030-103000000000"]
            ],
            "objects": [
                {
                    "model": "tests.sectionedpage",
                    "pk": 100,
                    "parent_id": 1,
                    "fields": {
                        "title": "How to boil an egg",
                        "show_in_menus": false,
                        "live": true,
                        "slug": "how-to-boil-an-egg",
                        "intro": "This is still how to boil an egg",
                        "sections": [102, 103],
                        "wagtail_admin_comments": []
                    }
                },
                {
                    "model": "tests.sectionedpagesection",
                    "pk": 102,
                    "fields": {
                        "sort_order": 0,
                        "title": "Boil the egg",
                        "body": "...",
                        "page": 100
                    }
                },
                {
                    "model": "tests.sectionedpagesection",
                    "pk": 103,
                    "fields": {
                        "sort_order": 1,
                        "title": "Eat the egg",
                        "body": "...",
                        "page": 100
                    }
                }
            ]
        }"""

        importer = ImportPlanner(root_page_source_pk=100, destination_parent_id=2)
        importer.add_json(data)
        importer.run()

        new_page = SectionedPage.objects.get(id=page_id)
        self.assertEqual(new_page.intro, "This is still how to boil an egg")
        self.assertEqual(new_page.sections.count(), 2)
        new_sections = new_page.sections.all()
        self.assertEqual(new_sections[0].id, section_2_id)
        self.assertEqual(new_sections[0].title, "Boil the egg")

        self.assertNotEqual(new_sections[1].id, section_1_id)
        self.assertEqual(new_sections[1].title, "Eat the egg")

    def test_import_page_with_comments(self):
        data = """{
            "ids_for_import": [
                ["wagtailcore.page", 100]
            ],
            "mappings": [
                ["wagtailcore.page", 100, "10000000-1000-1000-1000-100000000000"],
                ["wagtailcore.comment", 101, "10100000-1010-1010-1010-101000000000"],
                ["wagtailcore.commentreply", 102, "10200000-1020-1020-1020-102000000000"],
                ["auth.user", 1, "76a4de62-a697-11eb-8025-02b46b8cb81a"]
            ],
            "objects": [
                {
                    "model": "tests.simplepage",
                    "pk": 100,
                    "parent_id": 1,
                    "fields": {
                        "title": "How to boil an egg",
                        "show_in_menus": false,
                        "live": true,
                        "slug": "how-to-boil-an-egg",
                        "intro": "This is how to boil an egg",
                        "wagtail_admin_comments": [101]
                    }
                },
                {
                    "model": "wagtailcore.comment",
                    "pk": 101,
                    "fields": {
                        "text": "Not a fan",
                        "contentpath": "intro",
                        "page": 100,
                        "user": 1,
                        "created_at": "2021-04-26T13:58:07.892Z",
                        "updated_at": "2021-04-26T13:58:07.892Z",
                        "replies": [102]
                    }
                },
                {
                    "model": "wagtailcore.commentreply",
                    "pk": 102,
                    "fields": {
                        "text": "Actually, changed my mind",
                        "comment": 101,
                        "user": 1,
                        "created_at": "2021-05-26T13:58:07.892Z",
                        "updated_at": "2021-05-26T13:58:07.892Z"
                    }
                }
            ]
        }"""

        importer = ImportPlanner(root_page_source_pk=100, destination_parent_id=2)
        importer.add_json(data)
        importer.run()

        page = SimplePage.objects.get(url_path='/home/how-to-boil-an-egg/')

        self.assertEqual(page.wagtail_admin_comments.count(), 1)

        comment = page.wagtail_admin_comments.first()
        self.assertEqual(comment.replies.count(), 1)

        self.assertEqual(comment.contentpath, "intro")
        self.assertEqual(comment.text, "Not a fan")
        self.assertEqual(comment.replies.first().text, "Actually, changed my mind")

    def test_import_page_with_rich_text_link(self):
        data = """{
            "ids_for_import": [
                ["wagtailcore.page", 15]
            ],
            "mappings": [
                ["wagtailcore.page", 12, "11111111-1111-1111-1111-111111111111"],
                ["wagtailcore.page", 15, "01010101-0005-8765-7889-987889889898"]
            ],
            "objects": [
                {
                    "model": "tests.pagewithrichtext",
                    "pk": 15,
                    "parent_id": 12,
                    "fields": {
                        "title": "Imported page with rich text",
                        "show_in_menus": false,
                        "live": true,
                        "slug": "imported-rich-text-page",
                        "body": "<p>But I have a <a id=\\"12\\" linktype=\\"page\\">link</a></p>",
                        "wagtail_admin_comments": []
                    }
                }
            ]
        }"""

        importer = ImportPlanner(root_page_source_pk=1, destination_parent_id=None)
        importer.add_json(data)
        importer.run()

        page = PageWithRichText.objects.get(slug="imported-rich-text-page")

        # tests that a page link id is changed successfully when imported
        self.assertEqual(page.body, '<p>But I have a <a id="1" linktype="page">link</a></p>')

        # TODO: this should include an embed type as well once document/image import is added

    def test_import_page_with_unhandled_rich_text_feature(self):
        """
        Rich text fields with custom link handlers should be gracefully.

        If rich text includes custom link/embed types that do not implement
        `get_model', the import shouldn't fail.
        """
        data = Template(
            """{
                "ids_for_import": [
                    ["wagtailcore.page", 15]
                ],
                "mappings": [
                    ["wagtailcore.page", 12, "11111111-1111-1111-1111-111111111111"],
                    ["wagtailcore.page", 15, "01010101-0005-8765-7889-987889889898"]
                ],
                "objects": [
                    {
                        "model": "tests.pagewithrichtext",
                        "pk": 15,
                        "parent_id": 12,
                        "fields": {
                            "title": "Imported page with rich text",
                            "show_in_menus": false,
                            "live": true,
                            "slug": "imported-rich-text-page",
                            "body": "Hello <a id=\\"42\\" linktype=\\"$link_type\\">world</a>",
                            "wagtail_admin_comments": []
                        }
                    }
                ]
            }"""
        )

        for link_type in CUSTOM_LINK_TYPE_IDENTIFIERS:
            with self.subTest(link_type=link_type):
                importer = ImportPlanner(root_page_source_pk=1, destination_parent_id=None)
                importer.add_json(data.substitute(link_type=link_type))
                importer.run()

                page = PageWithRichText.objects.get(slug="imported-rich-text-page")

                # tests that the custom linktype is imported successfully
                self.assertEqual(page.body, f'Hello <a id="42" linktype="{link_type}">world</a>')

    def test_import_page_with_unhandled_rich_text_feature_stream_field(self):
        """
        Rich text blocks with custom link handlers should be gracefully.
        """

        data = Template(
            """{
                "ids_for_import": [["wagtailcore.page", 6]],
                "mappings": [
                    ["wagtailcore.page", 6, "0c7a9390-16cb-11ea-8000-0800278dc04d"],
                    ["wagtailcore.page", 300, "33333333-3333-3333-3333-333333333333"]
                ],
                "objects": [
                    {
                        "model": "tests.pagewithstreamfield",
                        "pk": 6,
                        "parent_id": 300,
                        "fields": {
                            "title": "Imported page with rich text",
                            "show_in_menus": false,
                            "live": true,
                            "slug": "imported-rich-text-page",
                            "body": "[{\\"type\\": \\"rich_text\\", \\"value\\": \\"Hello <a id=\\\\\\"42\\\\\\" linktype=\\\\\\"$link_type\\\\\\">world</a>\\", \\"id\\": \\"fc3b0d3d-d316-4271-9e31-84919558188a\\"}]",
                            "wagtail_admin_comments": []
                        }
                    }
                ]
            }"""
        )

        for link_type in CUSTOM_LINK_TYPE_IDENTIFIERS:
            importer = ImportPlanner(root_page_source_pk=1, destination_parent_id=None)
            importer.add_json(data.substitute(link_type=link_type))
            importer.run()

            page = PageWithStreamField.objects.get(slug="imported-rich-text-page")

            # tests that the custom linktype is imported successfully
            self.assertEqual(
                page.body[0].value.source,
                f'Hello <a id="42" linktype="{link_type}">world</a>',
            )

    def test_import_page_with_null_rich_text(self):
        data = """{
            "ids_for_import": [
                ["wagtailcore.page", 15]
            ],
            "mappings": [
                ["wagtailcore.page", 12, "11111111-1111-1111-1111-111111111111"],
                ["wagtailcore.page", 15, "01010101-0005-8765-7889-987889889898"]
            ],
            "objects": [
                {
                    "model": "tests.pagewithrichtext",
                    "pk": 15,
                    "parent_id": 12,
                    "fields": {
                        "title": "Imported page with null rich text",
                        "show_in_menus": false,
                        "live": true,
                        "slug": "imported-rich-text-page",
                        "body": null,
                        "wagtail_admin_comments": []
                    }
                }
            ]
        }"""

        importer = ImportPlanner(root_page_source_pk=1, destination_parent_id=None)
        importer.add_json(data)
        importer.run()

        page = PageWithRichText.objects.get(slug="imported-rich-text-page")
        self.assertEqual(page.body, None)

    def test_do_not_import_pages_outside_of_selected_root(self):
        # Source page 13 is a page we don't have at the destination, but it's not in ids_for_import
        # (i.e. it's outside of the selected import root), so we shouldn't import it, and should
        # remove links in rich text
        data = """{
            "ids_for_import": [
                ["wagtailcore.page", 15]
            ],
            "mappings": [
                ["wagtailcore.page", 12, "11111111-1111-1111-1111-111111111111"],
                ["wagtailcore.page", 13, "13131313-1313-1313-1313-131313131313"],
                ["wagtailcore.page", 15, "01010101-0005-8765-7889-987889889898"]
            ],
            "objects": [
                {
                    "model": "tests.pagewithrichtext",
                    "pk": 15,
                    "parent_id": 12,
                    "fields": {
                        "title": "Imported page with rich text",
                        "show_in_menus": false,
                        "live": true,
                        "slug": "imported-rich-text-page",
                        "body": "<p>But I have a <a id=\\"13\\" linktype=\\"page\\">link</a></p>",
                        "wagtail_admin_comments": []
                    }
                }
            ]
        }"""

        importer = ImportPlanner(root_page_source_pk=1, destination_parent_id=None)
        importer.add_json(data)
        importer.run()

        page = PageWithRichText.objects.get(slug="imported-rich-text-page")

        # tests that the page link tag is removed, as the page does not exist on the destination
        self.assertEqual(page.body, '<p>But I have a link</p>')

    def test_import_page_with_streamfield_page_links(self):
        data = """{
                "ids_for_import": [
                    ["wagtailcore.page", 6]
                ],
                "mappings": [
                    ["wagtailcore.page", 6, "0c7a9390-16cb-11ea-8000-0800278dc04d"],
                    ["wagtailcore.page", 300, "33333333-3333-3333-3333-333333333333"],
                    ["wagtailcore.page", 200, "22222222-2222-2222-2222-222222222222"],
                    ["wagtailcore.page", 500, "00017017-5555-5555-5555-555555555555"],
                    ["wagtailcore.page", 100, "11111111-1111-1111-1111-111111111111"]
                ],
                "objects": [
                    {
                        "model": "tests.pagewithstreamfield",
                        "pk": 6,
                        "fields": {
                            "title": "I have a streamfield",
                            "slug": "i-have-a-streamfield",
                            "live": true,
                            "seo_title": "",
                            "show_in_menus": false,
                            "wagtail_admin_comments": [],
                            "search_description": "",
                            "body": "[{\\"type\\": \\"link_block\\", \\"value\\": {\\"page\\": 100, \\"text\\": \\"Test\\"}, \\"id\\": \\"fc3b0d3d-d316-4271-9e31-84919558188a\\"}, {\\"type\\": \\"page\\", \\"value\\": 200, \\"id\\": \\"c6d07d3a-72d4-445e-8fa5-b34107291176\\"}, {\\"type\\": \\"stream\\", \\"value\\": [{\\"type\\": \\"page\\", \\"value\\": 300, \\"id\\": \\"8c0d7de7-4f77-4477-be67-7d990d0bfb82\\"}], \\"id\\": \\"21ffe52a-c0fc-4ecc-92f1-17b356c9cc94\\"}, {\\"type\\": \\"list_of_pages\\", \\"value\\": [500], \\"id\\": \\"17b972cb-a952-4940-87e2-e4eb00703997\\"}]"},
                            "parent_id": 300
                        }
                    ]
                }"""
        importer = ImportPlanner(root_page_source_pk=1, destination_parent_id=None)
        importer.add_json(data)
        importer.run()

        page = PageWithStreamField.objects.get(slug="i-have-a-streamfield")

        imported_streamfield = page.body.stream_block.get_prep_value(page.body)

        # Check that PageChooserBlock ids are converted correctly to those on the destination site
        self.assertEqual(imported_streamfield, [{'type': 'link_block', 'value': {'page': 1, 'text': 'Test'}, 'id': 'fc3b0d3d-d316-4271-9e31-84919558188a'}, {'type': 'page', 'value': 2, 'id': 'c6d07d3a-72d4-445e-8fa5-b34107291176'}, {'type': 'stream', 'value': [{'type': 'page', 'value': 3, 'id': '8c0d7de7-4f77-4477-be67-7d990d0bfb82'}], 'id': '21ffe52a-c0fc-4ecc-92f1-17b356c9cc94'}, {'type': 'list_of_pages', 'value': [5], 'id': '17b972cb-a952-4940-87e2-e4eb00703997'}])

    def test_import_page_with_document_chooser_block(self):
        data = """{
                "ids_for_import": [
                    ["wagtailcore.page", 6]
                ],
                "mappings": [
                    ["wagtailcore.page", 6, "0c7a9390-16cb-11ea-8000-0800278dc04d"],
                    ["wagtailcore.page", 300, "33333333-3333-3333-3333-333333333333"],
                    ["wagtaildocs.document", 1, "ffffffff-ffff-ffff-ffff-ffffffffffff"]
                ],
                "objects": [
                    {
                        "model": "tests.pagewithstreamfield",
                        "pk": 6,
                        "fields": {
                            "title": "I have a streamfield",
                            "slug": "i-have-a-streamfield",
                            "live": true,
                            "seo_title": "",
                            "show_in_menus": false,
                            "wagtail_admin_comments": [],
                            "search_description": "",
                            "body": "[{\\"type\\": \\"document\\", \\"value\\": 1, \\"id\\": \\"17b972cb-a952-4940-87e2-e4eb00703997\\"}]"
                        },
                        "parent_id": 300
                    }
                ]
        }"""
        importer = ImportPlanner(root_page_source_pk=1, destination_parent_id=None)
        importer.add_json(data)
        importer.run()
        page = PageWithStreamField.objects.get(slug="i-have-a-streamfield")

        imported_streamfield = page.body.stream_block.get_prep_value(page.body)

        # Check that DocumentChooserBlock ids are converted correctly to those on the destination site
        self.assertEqual(
            imported_streamfield,
            [
                {
                    'id': '17b972cb-a952-4940-87e2-e4eb00703997',
                    'type': 'document',
                    'value': 1,
                },
            ],
        )

    def test_import_page_with_streamfield_page_links_where_linked_pages_not_imported(self):
        data = """{
                "ids_for_import": [
                    ["wagtailcore.page", 6]
                ],
                "mappings": [
                    ["wagtailcore.page", 6, "0c7a9390-16cb-11ea-8000-0800278dc04d"],
                    ["wagtailcore.page", 300, "33333333-3333-3333-3333-333333333333"],
                    ["wagtailcore.page", 200, "22222222-2222-2222-2222-222222222229"],
                    ["wagtailcore.page", 500, "00017017-5555-5555-5555-555555555559"],
                    ["wagtailcore.page", 100, "11111111-1111-1111-1111-111111111119"]
                ],
                "objects": [
                    {
                        "model": "tests.pagewithstreamfield",
                        "pk": 6,
                        "fields": {
                            "title": "I have a streamfield",
                            "slug": "i-have-a-streamfield",
                            "live": true,
                            "seo_title": "",
                            "show_in_menus": false,
                            "wagtail_admin_comments": [],
                            "search_description": "",
                            "body": "[{\\"type\\": \\"integer\\", \\"value\\": 0, \\"id\\": \\"aad07d3a-72d4-445e-8fa5-b34107291199\\"}, {\\"type\\": \\"link_block\\", \\"value\\": {\\"page\\": 100, \\"text\\": \\"Test\\"}, \\"id\\": \\"fc3b0d3d-d316-4271-9e31-84919558188a\\"}, {\\"type\\": \\"page\\", \\"value\\": 200, \\"id\\": \\"c6d07d3a-72d4-445e-8fa5-b34107291176\\"}, {\\"type\\": \\"stream\\", \\"value\\": [{\\"type\\": \\"page\\", \\"value\\": 300, \\"id\\": \\"8c0d7de7-4f77-4477-be67-7d990d0bfb82\\"}], \\"id\\": \\"21ffe52a-c0fc-4ecc-92f1-17b356c9cc94\\"}, {\\"type\\": \\"list_of_pages\\", \\"value\\": [500], \\"id\\": \\"17b972cb-a952-4940-87e2-e4eb00703997\\"}]"},
                            "parent_id": 300
                        }
                    ]
                }"""
        importer = ImportPlanner(root_page_source_pk=1, destination_parent_id=None)
        importer.add_json(data)
        importer.run()

        page = PageWithStreamField.objects.get(slug="i-have-a-streamfield")

        imported_streamfield = page.body.stream_block.get_prep_value(page.body)

        # The PageChooserBlock has required=True, so when its value is removed, the block should also be removed
        self.assertNotIn({'type': 'page', 'value': None, 'id': 'c6d07d3a-72d4-445e-8fa5-b34107291176'}, imported_streamfield)

        # Test that 0 values are not removed, only None
        self.assertIn({'type': 'integer', 'value': 0, 'id': 'aad07d3a-72d4-445e-8fa5-b34107291199'}, imported_streamfield)

        # By contrast, the PageChooserBlock in the link_block has required=False, so just the block's value should be removed instead
        self.assertIn({'type': 'link_block', 'value': {'page': None, 'text': 'Test'}, 'id': 'fc3b0d3d-d316-4271-9e31-84919558188a'}, imported_streamfield)

        # The ListBlock should now be empty, as the (required) PageChooserBlocks inside have had their values set to None
        self.assertIn({'type': 'list_of_pages', 'value': [], 'id': '17b972cb-a952-4940-87e2-e4eb00703997'}, imported_streamfield)


    def test_import_page_with_streamfield_rich_text_block(self):
        # Check that ids in RichTextBlock within a StreamField are converted properly

        data = """{"ids_for_import": [["wagtailcore.page", 6]], "mappings": [["wagtailcore.page", 6, "a231303a-1754-11ea-8000-0800278dc04d"], ["wagtailcore.page", 100, "11111111-1111-1111-1111-111111111111"]], "objects": [{"model": "tests.pagewithstreamfield", "pk": 6, "fields": {"title": "My streamfield rich text block has a link", "slug": "my-streamfield-rich-text-block-has-a-link", "wagtail_admin_comments": [], "live": true, "seo_title": "", "show_in_menus": false, "search_description": "", "body": "[{\\"type\\": \\"rich_text\\", \\"value\\": \\"<p>I link to a <a id=\\\\\\"100\\\\\\" linktype=\\\\\\"page\\\\\\">page</a>.</p>\\", \\"id\\": \\"7d4ee3d4-9213-4319-b984-45be4ded8853\\"}]"}, "parent_id": 100}]}"""
        importer = ImportPlanner(root_page_source_pk=1, destination_parent_id=None)
        importer.add_json(data)
        importer.run()

        page = PageWithStreamField.objects.get(slug="my-streamfield-rich-text-block-has-a-link")

        imported_streamfield = page.body.stream_block.get_prep_value(page.body)

        self.assertEqual(imported_streamfield, [{'type': 'rich_text', 'value': '<p>I link to a <a id="1" linktype="page">page</a>.</p>', 'id': '7d4ee3d4-9213-4319-b984-45be4ded8853'}])

    def test_import_page_with_new_list_block_format(self):
        # Check that ids in a ListBlock with the uuid format within a StreamField are converted properly
        data = """{"ids_for_import": [["wagtailcore.page", 6]], "mappings": [["wagtailcore.page", 6, "a231303a-1754-11ea-8000-0800278dc04d"], ["wagtailcore.page", 100, "11111111-1111-1111-1111-111111111111"]], "objects": [{"model": "tests.pagewithstreamfield", "pk": 6, "fields": {"title": "My streamfield list block has a link", "slug": "my-streamfield-block-has-a-link", "wagtail_admin_comments": [], "live": true, "seo_title": "", "show_in_menus": false, "search_description": "", "body": "[{\\"type\\": \\"list_of_captioned_pages\\", \\"value\\": [{\\"type\\": \\"item\\", \\"value\\": {\\"page\\": 100, \\"text\\": \\"a caption\\"}, \\"id\\": \\"8c0d7de7-4f77-4477-be67-7d990d0bfb82\\"}], \\"id\\": \\"21ffe52a-c0fc-4ecc-92f1-17b356c9cc94\\"}]"}, "parent_id": 100}]}"""
        importer = ImportPlanner(root_page_source_pk=1, destination_parent_id=None)
        importer.add_json(data)
        importer.run()

        page = PageWithStreamField.objects.get(slug="my-streamfield-block-has-a-link")

        imported_streamfield = page.body.stream_block.get_prep_value(page.body)

        self.assertEqual(imported_streamfield, [{'type': 'list_of_captioned_pages', 'value': [{'type': 'item', 'value': {'page': 1, 'text': 'a caption'}, 'id': '8c0d7de7-4f77-4477-be67-7d990d0bfb82'}], 'id': '21ffe52a-c0fc-4ecc-92f1-17b356c9cc94'}])

    @mock.patch('requests.get')
    def test_import_image_with_file(self, get):
        get.return_value.status_code = 200
        get.return_value.content = b'my test image file contents'

        IDMapping.objects.get_or_create(
            uid="f91cb31c-1751-11ea-8000-0800278dc04d",
            defaults={
                'content_type': ContentType.objects.get_for_model(Collection),
                'local_id':  Collection.objects.get().id,
            }
        )

        data = """{
            "ids_for_import": [
                ["wagtailimages.image", 53]
            ],
            "mappings": [
                ["wagtailcore.collection", 3, "f91cb31c-1751-11ea-8000-0800278dc04d"],
                ["wagtailimages.image", 53, "f91debc6-1751-11ea-8001-0800278dc04d"]
            ],
            "objects": [
                {
                    "model": "wagtailcore.collection",
                    "pk": 3,
                    "fields": {
                        "name": "Root"
                    },
                    "parent_id": null
                },
                {
                    "model": "wagtailimages.image",
                    "pk": 53,
                    "fields": {
                        "collection": 3,
                        "title": "Lightnin' Hopkins",
                        "file": {
                            "download_url": "https://wagtail.io/media/original_images/lightnin_hopkins.jpg",
                            "size": 18521,
                            "hash": "e4eab12cc50b6b9c619c9ddd20b61d8e6a961ada"
                        },
                        "width": 150,
                        "height": 162,
                        "created_at": "2019-04-01T07:31:21.251Z",
                        "uploaded_by_user": null,
                        "focal_point_x": null,
                        "focal_point_y": null,
                        "focal_point_width": null,
                        "focal_point_height": null,
                        "file_size": 18521,
                        "file_hash": "e4eab12cc50b6b9c619c9ddd20b61d8e6a961ada",
                        "tags": "[]",
                        "tagged_items": []
                    }
                }
            ]
        }"""

        importer = ImportPlanner(root_page_source_pk=1, destination_parent_id=None)
        importer.add_json(data)
        importer.run()

        # Check the image was imported
        get.assert_called()
        image = Image.objects.get()
        self.assertEqual(image.title, "Lightnin' Hopkins")
        self.assertEqual(image.file.read(), b'my test image file contents')

        # TODO: We should verify these
        self.assertEqual(image.file_size, 18521)
        self.assertEqual(image.file_hash, "e4eab12cc50b6b9c619c9ddd20b61d8e6a961ada")

    @mock.patch('requests.get')
    def test_import_image_with_file_without_root_collection_mapping(self, get):
        get.return_value.status_code = 200
        get.return_value.content = b'my test image file contents'

        data = """{
            "ids_for_import": [
                ["wagtailimages.image", 53]
            ],
            "mappings": [
                ["wagtailcore.collection", 3, "f91cb31c-1751-11ea-8000-0800278dc04d"],
                ["wagtailimages.image", 53, "f91debc6-1751-11ea-8001-0800278dc04d"]
            ],
            "objects": [
                {
                    "model": "wagtailcore.collection",
                    "pk": 3,
                    "fields": {
                        "name": "the other root"
                    },
                    "parent_id": null
                },
                {
                    "model": "wagtailimages.image",
                    "pk": 53,
                    "fields": {
                        "collection": 3,
                        "title": "Lightnin' Hopkins",
                        "file": {
                            "download_url": "https://wagtail.io/media/original_images/lightnin_hopkins.jpg",
                            "size": 18521,
                            "hash": "e4eab12cc50b6b9c619c9ddd20b61d8e6a961ada"
                        },
                        "width": 150,
                        "height": 162,
                        "created_at": "2019-04-01T07:31:21.251Z",
                        "uploaded_by_user": null,
                        "focal_point_x": null,
                        "focal_point_y": null,
                        "focal_point_width": null,
                        "focal_point_height": null,
                        "file_size": 18521,
                        "file_hash": "e4eab12cc50b6b9c619c9ddd20b61d8e6a961ada",
                        "tags": "[]",
                        "tagged_items": []
                    }
                }
            ]
        }"""

        importer = ImportPlanner(root_page_source_pk=1, destination_parent_id=None)
        importer.add_json(data)
        importer.run()

        # Check the image was imported
        get.assert_called()
        image = Image.objects.get()
        self.assertEqual(image.title, "Lightnin' Hopkins")
        self.assertEqual(image.file.read(), b'my test image file contents')

        # It should be in the existing root collection (no new collection should be created)
        self.assertEqual(image.collection.name, "Root")
        self.assertEqual(Collection.objects.count(), 1)

        # TODO: We should verify these
        self.assertEqual(image.file_size, 18521)
        self.assertEqual(image.file_hash, "e4eab12cc50b6b9c619c9ddd20b61d8e6a961ada")

    @mock.patch('requests.get')
    def test_existing_image_is_not_refetched(self, get):
        """
        If an incoming object has a FileField that reports the same size/hash as the existing
        file, we should not refetch the file
        """

        get.return_value.status_code = 200
        get.return_value.content = b'my test image file contents'

        with open(os.path.join(FIXTURES_DIR, 'wagtail.jpg'), 'rb') as f:
            image = Image.objects.create(
                title="Wagtail",
                file=ImageFile(f, name='wagtail.jpg')
            )

        IDMapping.objects.get_or_create(
            uid="f91debc6-1751-11ea-8001-0800278dc04d",
            defaults={
                'content_type': ContentType.objects.get_for_model(Image),
                'local_id': image.id,
            }
        )

        data = """{
            "ids_for_import": [
                ["wagtailimages.image", 53]
            ],
            "mappings": [
                ["wagtailcore.collection", 3, "f91cb31c-1751-11ea-8000-0800278dc04d"],
                ["wagtailimages.image", 53, "f91debc6-1751-11ea-8001-0800278dc04d"]
            ],
            "objects": [
                {
                    "model": "wagtailcore.collection",
                    "pk": 3,
                    "fields": {
                        "name": "root"
                    },
                    "parent_id": null
                },
                {
                    "model": "wagtailimages.image",
                    "pk": 53,
                    "fields": {
                        "collection": 3,
                        "title": "A lovely wagtail",
                        "file": {
                            "download_url": "https://wagtail.io/media/original_images/wagtail.jpg",
                            "size": 1160,
                            "hash": "45c5db99aea04378498883b008ee07528f5ae416"
                        },
                        "width": 32,
                        "height": 40,
                        "created_at": "2019-04-01T07:31:21.251Z",
                        "uploaded_by_user": null,
                        "focal_point_x": null,
                        "focal_point_y": null,
                        "focal_point_width": null,
                        "focal_point_height": null,
                        "file_size": 1160,
                        "file_hash": "45c5db99aea04378498883b008ee07528f5ae416",
                        "tags": "[]",
                        "tagged_items": []
                    }
                }
            ]
        }"""

        importer = ImportPlanner(root_page_source_pk=1, destination_parent_id=None)
        importer.add_json(data)
        importer.run()

        get.assert_not_called()
        image = Image.objects.get()
        # Metadata was updated...
        self.assertEqual(image.title, "A lovely wagtail")
        # but file is left alone (i.e. it has not been replaced with 'my test image file contents')
        self.assertEqual(image.file.size, 1160)

    @mock.patch('requests.get')
    def test_replace_image(self, get):
        """
        If an incoming object has a FileField that reports a different size/hash to the existing
        file, we should fetch it and update the field
        """

        get.return_value.status_code = 200
        get.return_value.content = b'my test image file contents'

        with open(os.path.join(FIXTURES_DIR, 'wagtail.jpg'), 'rb') as f:
            image = Image.objects.create(
                title="Wagtail",
                file=ImageFile(f, name='wagtail.jpg')
            )

        IDMapping.objects.get_or_create(
            uid="f91debc6-1751-11ea-8001-0800278dc04d",
            defaults={
                'content_type': ContentType.objects.get_for_model(Image),
                'local_id': image.id,
            }
        )

        data = """{
            "ids_for_import": [
                ["wagtailimages.image", 53]
            ],
            "mappings": [
                ["wagtailcore.collection", 3, "f91cb31c-1751-11ea-8000-0800278dc04d"],
                ["wagtailimages.image", 53, "f91debc6-1751-11ea-8001-0800278dc04d"]
            ],
            "objects": [
                {
                    "model": "wagtailcore.collection",
                    "pk": 3,
                    "fields": {
                        "name": "root"
                    },
                    "parent_id": null
                },
                {
                    "model": "wagtailimages.image",
                    "pk": 53,
                    "fields": {
                        "collection": 3,
                        "title": "A lovely wagtail",
                        "file": {
                            "download_url": "https://wagtail.io/media/original_images/wagtail.jpg",
                            "size": 27,
                            "hash": "e4eab12cc50b6b9c619c9ddd20b61d8e6a961ada"
                        },
                        "width": 32,
                        "height": 40,
                        "created_at": "2019-04-01T07:31:21.251Z",
                        "uploaded_by_user": null,
                        "focal_point_x": null,
                        "focal_point_y": null,
                        "focal_point_width": null,
                        "focal_point_height": null,
                        "file_size": 27,
                        "file_hash": "e4eab12cc50b6b9c619c9ddd20b61d8e6a961ada",
                        "tags": "[]",
                        "tagged_items": []
                    }
                }
            ]
        }"""

        importer = ImportPlanner(root_page_source_pk=1, destination_parent_id=None)
        importer.add_json(data)
        importer.run()

        get.assert_called()
        image = Image.objects.get()
        self.assertEqual(image.title, "A lovely wagtail")
        self.assertEqual(image.file.read(), b'my test image file contents')

    @mock.patch('requests.get')
    def test_updated_image_renditions_cleared(self, get):
        """
        If we update an Image file, we should clear any renditions that were generated from
        the older version of the file.
        """

        get.return_value.status_code = 200
        get.return_value.content = b'my test image file contents'

        with open(os.path.join(FIXTURES_DIR, 'wagtail.jpg'), 'rb') as f:
            image = Image.objects.create(
                title="Wagtail",
                file=ImageFile(f, name='wagtail.jpg')
            )

        rendition = image.get_rendition("fill-165x165")
        self.assertIn(rendition, image.renditions.all())

        IDMapping.objects.get_or_create(
            uid="f91debc6-1751-11ea-8001-0800278dc04d",
            defaults={
                'content_type': ContentType.objects.get_for_model(Image),
                'local_id': image.id,
            }
        )

        data = """{
            "ids_for_import": [
                ["wagtailimages.image", 53]
            ],
            "mappings": [
                ["wagtailcore.collection", 3, "f91cb31c-1751-11ea-8000-0800278dc04d"],
                ["wagtailimages.image", 53, "f91debc6-1751-11ea-8001-0800278dc04d"]
            ],
            "objects": [
                {
                    "model": "wagtailcore.collection",
                    "pk": 3,
                    "fields": {
                        "name": "root"
                    },
                    "parent_id": null
                },
                {
                    "model": "wagtailimages.image",
                    "pk": 53,
                    "fields": {
                        "collection": 3,
                        "title": "A lovely wagtail",
                        "file": {
                            "download_url": "https://wagtail.io/media/original_images/wagtail.jpg",
                            "size": 27,
                            "hash": "e4eab12cc50b6b9c619c9ddd20b61d8e6a961ada"
                        },
                        "width": 32,
                        "height": 40,
                        "created_at": "2019-04-01T07:31:21.251Z",
                        "uploaded_by_user": null,
                        "focal_point_x": null,
                        "focal_point_y": null,
                        "focal_point_width": null,
                        "focal_point_height": null,
                        "file_size": 27,
                        "file_hash": "e4eab12cc50b6b9c619c9ddd20b61d8e6a961ada",
                        "tags": "[]",
                        "tagged_items": []
                    }
                }
            ]
        }"""

        importer = ImportPlanner(root_page_source_pk=1, destination_parent_id=None)
        importer.add_json(data)
        importer.run()

        get.assert_called()
        image = Image.objects.get()
        self.assertNotIn(rendition, image.renditions.all())

    def test_renditions_not_cleared_if_file_unchanged(self):
        """
        If we update an Image, but not the file, we shouldn't clear the renditions
        """

        with open(os.path.join(FIXTURES_DIR, 'wagtail.jpg'), 'rb') as f:
            image = Image.objects.create(
                title="Wagtail",
                file=ImageFile(f, name='wagtail.jpg')
            )

        original_image_hash = image.get_file_hash()
        rendition = image.get_rendition("fill-165x165")
        self.assertIn(rendition, image.renditions.all())

        IDMapping.objects.get_or_create(
            uid="f91debc6-1751-11ea-8001-0800278dc04d",
            defaults={
                'content_type': ContentType.objects.get_for_model(Image),
                'local_id': image.id,
            }
        )

        data = f"""{{
            "ids_for_import": [
                ["wagtailimages.image", 53]
            ],
            "mappings": [
                ["wagtailcore.collection", 3, "f91cb31c-1751-11ea-8000-0800278dc04d"],
                ["wagtailimages.image", 53, "f91debc6-1751-11ea-8001-0800278dc04d"]
            ],
            "objects": [
                {{
                    "model": "wagtailcore.collection",
                    "pk": 3,
                    "fields": {{
                        "name": "root"
                    }},
                    "parent_id": null
                }},
                {{
                    "model": "wagtailimages.image",
                    "pk": 53,
                    "fields": {{
                        "collection": 3,
                        "title": "A lovely wagtail",
                        "file": {{
                            "download_url": "https://wagtail.io/media/original_images/wagtail.jpg",
                            "size": 27,
                            "hash": "{original_image_hash}"
                        }},
                        "width": 32,
                        "height": 40,
                        "created_at": "2019-04-01T07:31:21.251Z",
                        "uploaded_by_user": null,
                        "focal_point_x": null,
                        "focal_point_y": null,
                        "focal_point_width": null,
                        "focal_point_height": null,
                        "file_size": 27,
                        "file_hash": "e4eab12cc50b6b9c619c9ddd20b61d8e6a961ada",
                        "tags": "[]",
                        "tagged_items": []
                    }}
                }}
            ]
        }}"""

        importer = ImportPlanner(root_page_source_pk=1, destination_parent_id=None)
        importer.add_json(data)
        importer.run()

        image = Image.objects.get()
        self.assertIn(rendition, image.renditions.all())

    def test_import_collection(self):
        root_collection = Collection.objects.get()

        IDMapping.objects.get_or_create(
            uid="f91cb31c-1751-11ea-8000-0800278dc04d",
            defaults={
                'content_type': ContentType.objects.get_for_model(Collection),
                'local_id':  root_collection.id,
            }
        )

        data = """{
            "ids_for_import": [
                ["wagtailcore.collection", 4]
            ],
            "mappings": [
                ["wagtailcore.collection", """ + str(root_collection.id) + """, "f91cb31c-1751-11ea-8000-0800278dc04d"],
                ["wagtailcore.collection", 4, "8a1d3afd-3fa2-4309-9dc7-6d31902174ca"]
            ],
            "objects": [
                {
                    "model": "wagtailcore.collection",
                    "pk": 4,
                    "fields": {
                        "name": "New collection"
                    },
                    "parent_id": """ + str(root_collection.id) + """
                }
            ]
        }"""

        importer = ImportPlanner(root_page_source_pk=1, destination_parent_id=None)
        importer.add_json(data)
        importer.run()

        # Check the new collection was imported
        collection = Collection.objects.get(name="New collection")
        self.assertEqual(collection.get_parent(), root_collection)

    def test_import_collection_without_root_collection_mapping(self):
        root_collection = Collection.objects.get()
        data = """{
            "ids_for_import": [
                ["wagtailcore.collection", 4]
            ],
            "mappings": [
                ["wagtailcore.collection", 1, "f91cb31c-1751-11ea-8000-0800278dc04d"],
                ["wagtailcore.collection", 4, "8a1d3afd-3fa2-4309-9dc7-6d31902174ca"]
            ],
            "objects": [
                {
                    "model": "wagtailcore.collection",
                    "pk": 4,
                    "fields": {
                        "name": "New collection"
                    },
                    "parent_id": 1
                },
                {
                    "model": "wagtailcore.collection",
                    "pk": 1,
                    "fields": {
                        "name": "source site root"
                    },
                    "parent_id": null
                }
            ]
        }"""

        importer = ImportPlanner(root_page_source_pk=1, destination_parent_id=None)
        importer.add_json(data)
        importer.run()

        # Check the new collection was imported into the existing root collection
        collection = Collection.objects.get(name="New collection")
        self.assertEqual(collection.get_parent(), root_collection)
        # Only the root and the imported collection should exist
        self.assertEqual(Collection.objects.count(), 2)

    def test_import_page_with_parental_many_to_many(self):
        # Test that a page with a ParentalManyToManyField has its ids translated to the destination site's appropriately
        data = """{
            "ids_for_import": [["wagtailcore.page", 6]],
            "mappings": [
                ["tests.advert", 200, "adadadad-2222-2222-2222-222222222222"],
                ["wagtailcore.page", 6, "a98b0848-1a96-11ea-8001-0800278dc04d"],
                ["tests.advert", 300, "adadadad-3333-3333-3333-333333333333"]
            ],
            "objects": [
                {"model": "tests.pagewithparentalmanytomany", "pk": 6, "fields": {"title": "This page has lots of ads!", "slug": "this-page-has-lots-of-ads", "wagtail_admin_comments": [], "live": true, "seo_title": "", "show_in_menus": false, "search_description": "", "ads": [200, 300]}, "parent_id": 1},
                {
                    "model": "tests.advert",
                    "pk": 200,
                    "fields": {"slogan": "Buy a thing you definitely need!", "run_until": "2021-04-01T12:00:00Z", "run_from": null}
                },
                {
                    "model": "tests.advert",
                    "pk": 300,
                    "fields": {"slogan": "Buy a half-scale authentically hydrogen-filled replica of the Hindenburg!", "run_until": "1937-05-06T23:25:12Z", "run_from": null}
                }
            ]}
        """

        importer = ImportPlanner(root_page_source_pk=6, destination_parent_id=3)
        importer.add_json(data)
        importer.run()

        page = PageWithParentalManyToMany.objects.get(slug="this-page-has-lots-of-ads")

        advert_2 = Advert.objects.get(id=2)
        advert_3 = Advert.objects.get(id=3)

        self.assertEqual(set(page.ads.all()), {advert_2, advert_3})

        # advert is listed in WAGTAILTRANSFER_UPDATE_RELATED_MODELS, so changes to the advert should have been pulled in too
        self.assertEqual(advert_3.slogan, "Buy a half-scale authentically hydrogen-filled replica of the Hindenburg!")
        self.assertEqual(advert_3.run_until, datetime(1937, 5, 6, 23, 25, 12, tzinfo=timezone.utc))
        self.assertEqual(advert_3.run_from, None)

    def test_import_object_with_many_to_many(self):
        # Test that an imported object with a ManyToManyField has its ids converted to the destination site's
        data = """{
            "ids_for_import": [["tests.modelwithmanytomany", 1]],
            "mappings": [
                ["tests.advert", 200, "adadadad-2222-2222-2222-222222222222"],
                ["tests.advert", 300, "adadadad-3333-3333-3333-333333333333"],
                ["tests.modelwithmanytomany", 1, "6a5e5e52-1aa0-11ea-8002-0800278dc04d"]
            ],
            "objects": [
                {"model": "tests.modelwithmanytomany", "pk": 1, "fields": {"ads": [200, 300]}},
                {
                    "model": "tests.advert",
                    "pk": 200,
                    "fields": {"slogan": "Buy a thing you definitely need!", "run_until": "2021-04-01T12:00:00Z", "run_from": null}
                },
                {
                    "model": "tests.advert",
                    "pk": 300,
                    "fields": {"slogan": "Buy a half-scale authentically hydrogen-filled replica of the Hindenburg!", "run_until": "1937-05-06T23:25:12Z", "run_from": null}
                }
            ]}"""

        importer = ImportPlanner(root_page_source_pk=6, destination_parent_id=3)
        importer.add_json(data)
        importer.run()

        ad_holder = ModelWithManyToMany.objects.get(id=1)
        advert_2 = Advert.objects.get(id=2)
        advert_3 = Advert.objects.get(id=3)
        self.assertEqual(set(ad_holder.ads.all()), {advert_2, advert_3})

        # advert is listed in WAGTAILTRANSFER_UPDATE_RELATED_MODELS, so changes to the advert should have been pulled in too
        self.assertEqual(advert_3.slogan, "Buy a half-scale authentically hydrogen-filled replica of the Hindenburg!")
        self.assertEqual(advert_3.run_until, datetime(1937, 5, 6, 23, 25, 12, tzinfo=timezone.utc))
        self.assertEqual(advert_3.run_from, None)

    def test_import_with_field_based_lookup(self):
        data = """{
            "ids_for_import": [
                ["wagtailcore.page", 15]
            ],
            "mappings": [
                ["wagtailcore.page", 15, "00017017-5555-5555-5555-555555555555"],
                ["tests.advert", 11, "adadadad-1111-1111-1111-111111111111"],
                ["tests.author", 100, "b00cb00c-1111-1111-1111-111111111111"],
                ["tests.category", 101, ["Cars"]],
                ["tests.category", 102, ["Environment"]]
            ],
            "objects": [
                {
                    "model": "tests.sponsoredpage",
                    "pk": 15,
                    "parent_id": 1,
                    "fields": {
                        "title": "Oil is still great",
                        "show_in_menus": false,
                        "live": true,
                        "slug": "oil-is-still-great",
                        "advert": 11,
                        "intro": "yay fossil fuels and climate change",
                        "author": 100,
                        "categories": [101, 102],
                        "wagtail_admin_comments": []
                    }
                },
                {
                    "model": "tests.advert",
                    "pk": 11,
                    "fields": {
                        "slogan": "put a leopard in your tank",
                        "run_until": "2020-12-23T21:05:43Z",
                        "run_from": null
                    }
                },
                {
                    "model": "tests.author",
                    "pk": 100,
                    "fields": {
                        "name": "Jack Kerouac",
                        "bio": "Jack Kerouac's car has been fixed now."
                    }
                },
                {
                    "model": "tests.category",
                    "pk": 102,
                    "fields": {
                        "name": "Environment",
                        "colour": "green"
                    }
                }
            ]
        }"""

        importer = ImportPlanner(root_page_source_pk=15, destination_parent_id=None)
        importer.add_json(data)
        importer.run()

        updated_page = SponsoredPage.objects.get(url_path='/home/oil-is-still-great/')
        # The 'Cars' category should have been matched by name to the existing record
        self.assertEqual(updated_page.categories.get(name='Cars').colour, "red")
        # The 'Environment' category should have been created
        self.assertEqual(updated_page.categories.get(name='Environment').colour, "green")

    def test_skip_import_if_hard_dependency_on_non_imported_page(self):
        data = """{
            "ids_for_import": [
                ["wagtailcore.page", 20],
                ["wagtailcore.page", 21],
                ["wagtailcore.page", 23],
                ["wagtailcore.page", 24],
                ["wagtailcore.page", 25],
                ["wagtailcore.page", 26],
                ["wagtailcore.page", 27]
            ],
            "mappings": [
                ["wagtailcore.page", 20, "20202020-2020-2020-2020-202020202020"],
                ["wagtailcore.page", 21, "21212121-2121-2121-2121-212121212121"],
                ["wagtailcore.page", 23, "23232323-2323-2323-2323-232323232323"],
                ["wagtailcore.page", 24, "24242424-2424-2424-2424-242424242424"],
                ["wagtailcore.page", 25, "25252525-2525-2525-2525-252525252525"],
                ["wagtailcore.page", 26, "26262626-2626-2626-2626-262626262626"],
                ["wagtailcore.page", 27, "27272727-2727-2727-2727-272727272727"],
                ["wagtailcore.page", 30, "00017017-5555-5555-5555-555555555555"],
                ["wagtailcore.page", 31, "31313131-3131-3131-3131-313131313131"]
            ],
            "objects": [
                {
                    "model": "tests.simplepage",
                    "pk": 20,
                    "parent_id": 12,
                    "fields": {
                        "title": "hard dependency test",
                        "show_in_menus": false,
                        "live": true,
                        "slug": "hard-dependency-test",
                        "intro": "Testing hard dependencies on pages outside the imported root",
                        "wagtail_admin_comments": []
                    }
                },
                {
                    "model": "tests.redirectpage",
                    "pk": 21,
                    "parent_id": 20,
                    "fields": {
                        "title": "redirect to oil page",
                        "show_in_menus": false,
                        "live": true,
                        "slug": "redirect-to-oil-page",
                        "redirect_to": 30,
                        "wagtail_admin_comments": []
                    }
                },
                {
                    "model": "tests.redirectpage",
                    "pk": 23,
                    "parent_id": 20,
                    "fields": {
                        "title": "redirect to unimported page",
                        "show_in_menus": false,
                        "live": true,
                        "slug": "redirect-to-unimported-page",
                        "redirect_to": 31,
                        "wagtail_admin_comments": []
                    }
                },
                {
                    "model": "tests.redirectpage",
                    "pk": 24,
                    "parent_id": 20,
                    "fields": {
                        "title": "redirect to redirect to oil page",
                        "show_in_menus": false,
                        "live": true,
                        "slug": "redirect-to-redirect-to-oil-page",
                        "redirect_to": 21,
                        "wagtail_admin_comments": []
                    }
                },
                {
                    "model": "tests.redirectpage",
                    "pk": 25,
                    "parent_id": 20,
                    "fields": {
                        "title": "redirect to redirect to unimported page",
                        "show_in_menus": false,
                        "live": true,
                        "slug": "redirect-to-redirect-to-unimported-page",
                        "redirect_to": 23,
                        "wagtail_admin_comments": []
                    }
                },
                {
                    "model": "tests.redirectpage",
                    "pk": 26,
                    "parent_id": 20,
                    "fields": {
                        "title": "pork redirecting to lamb",
                        "show_in_menus": false,
                        "live": true,
                        "slug": "pork-redirecting-to-lamb",
                        "redirect_to": 27,
                        "wagtail_admin_comments": []
                    }
                },
                {
                    "model": "tests.redirectpage",
                    "pk": 27,
                    "parent_id": 20,
                    "fields": {
                        "title": "lamb redirecting to pork",
                        "show_in_menus": false,
                        "live": true,
                        "slug": "lamb-redirecting-to-pork",
                        "redirect_to": 26,
                        "wagtail_admin_comments": []
                    }
                }
            ]
        }"""

        importer = ImportPlanner(root_page_source_pk=20, destination_parent_id=2)
        importer.add_json(data)
        importer.run()

        # A non-nullable FK to an existing page outside the imported root is fine
        redirect_to_oil_page = RedirectPage.objects.get(slug='redirect-to-oil-page')
        self.assertEqual(redirect_to_oil_page.redirect_to.slug, 'oil-is-great')

        # A non-nullable FK to a non-existing page outside the imported root will prevent import
        self.assertFalse(RedirectPage.objects.filter(slug='redirect-to-unimported-page').exists())

        # We can also handle FKs to pages being created in the import
        redirect_to_redirect_to_oil_page = RedirectPage.objects.get(slug='redirect-to-redirect-to-oil-page')
        self.assertEqual(redirect_to_redirect_to_oil_page.redirect_to.slug, 'redirect-to-oil-page')

        # Failure to create a page will also propagate to pages with a hard dependency on it
        self.assertFalse(RedirectPage.objects.filter(slug='redirect-to-redirect-to-unimported-page').exists())

        # Circular references will be caught and pages not created
        self.assertFalse(RedirectPage.objects.filter(slug='pork-redirecting-to-lamb').exists())
        self.assertFalse(RedirectPage.objects.filter(slug='lamb-redirecting-to-pork').exists())

    def test_circular_references_in_rich_text(self):
        data = """{
            "ids_for_import": [
                ["wagtailcore.page", 20],
                ["wagtailcore.page", 21],
                ["wagtailcore.page", 23]
            ],
            "mappings": [
                ["wagtailcore.page", 20, "20202020-2020-2020-2020-202020202020"],
                ["wagtailcore.page", 21, "21212121-2121-2121-2121-212121212121"],
                ["wagtailcore.page", 23, "23232323-2323-2323-2323-232323232323"]
            ],
            "objects": [
                {
                    "model": "tests.simplepage",
                    "pk": 20,
                    "parent_id": 12,
                    "fields": {
                        "title": "circular dependency test",
                        "show_in_menus": false,
                        "live": true,
                        "slug": "circular-dependency-test",
                        "intro": "Testing circular dependencies in rich text links",
                        "wagtail_admin_comments": []
                    }
                },
                {
                    "model": "tests.pagewithrichtext",
                    "pk": 21,
                    "parent_id": 20,
                    "fields": {
                        "title": "Bill's page",
                        "show_in_menus": false,
                        "live": true,
                        "slug": "bill",
                        "body": "<p>Have you met my friend <a id=\\"23\\" linktype=\\"page\\">Ben</a>?</p>",
                        "wagtail_admin_comments": []
                    }
                },
                {
                    "model": "tests.pagewithrichtext",
                    "pk": 23,
                    "parent_id": 20,
                    "fields": {
                        "title": "Ben's page",
                        "show_in_menus": false,
                        "live": true,
                        "slug": "ben",
                        "body": "<p>Have you met my friend <a id=\\"21\\" linktype=\\"page\\">Bill</a>?</p>",
                        "wagtail_admin_comments": []
                    }
                }
            ]
        }"""

        importer = ImportPlanner(root_page_source_pk=20, destination_parent_id=2)
        importer.add_json(data)
        importer.run()

        # Both pages should have been created
        bill_page = PageWithRichText.objects.get(slug='bill')
        ben_page = PageWithRichText.objects.get(slug='ben')

        # At least one of them (i.e. the second one to be created) should have a valid link to the other
        self.assertTrue(
            bill_page.body == """<p>Have you met my friend <a id="%d" linktype="page">Ben</a>?</p>""" % ben_page.id
            or
            ben_page.body == """<p>Have you met my friend <a id="%d" linktype="page">Bill</a>?</p>""" % bill_page.id
        )

    def test_omitting_references_in_m2m_relations(self):
        data = """{
            "ids_for_import": [
                ["wagtailcore.page", 20],
                ["wagtailcore.page", 21],
                ["wagtailcore.page", 23]
            ],
            "mappings": [
                ["wagtailcore.page", 20, "20202020-2020-2020-2020-202020202020"],
                ["wagtailcore.page", 21, "21212121-2121-2121-2121-212121212121"],
                ["wagtailcore.page", 23, "23232323-2323-2323-2323-232323232323"],
                ["wagtailcore.page", 30, "00017017-5555-5555-5555-555555555555"],
                ["wagtailcore.page", 31, "31313131-3131-3131-3131-313131313131"]
            ],
            "objects": [
                {
                    "model": "tests.simplepage",
                    "pk": 20,
                    "parent_id": 12,
                    "fields": {
                        "title": "m2m reference test",
                        "show_in_menus": false,
                        "live": true,
                        "slug": "m2m-reference-test",
                        "intro": "Testing references and dependencies on m2m relations",
                        "wagtail_admin_comments": []
                    }
                },
                {
                    "model": "tests.simplepage",
                    "pk": 21,
                    "parent_id": 20,
                    "fields": {
                        "title": "vinegar",
                        "show_in_menus": false,
                        "live": true,
                        "slug": "vinegar",
                        "intro": "it's pickling time",
                        "wagtail_admin_comments": []
                    }
                },
                {
                    "model": "tests.pagewithrelatedpages",
                    "pk": 23,
                    "parent_id": 20,
                    "fields": {
                        "title": "salad dressing",
                        "show_in_menus": false,
                        "live": true,
                        "slug": "salad-dressing",
                        "related_pages": [21,30,31],
                        "wagtail_admin_comments": []
                    }
                }
            ]
        }"""

        importer = ImportPlanner(root_page_source_pk=20, destination_parent_id=2)
        importer.add_json(data)
        importer.run()

        salad_dressing_page = PageWithRelatedPages.objects.get(slug='salad-dressing')
        oil_page = Page.objects.get(slug='oil-is-great')
        vinegar_page = Page.objects.get(slug='vinegar')

        # salad_dressing_page's related_pages should include the oil (id=30) and vinegar (id=21)
        # pages, but not the missing and not-to-be-imported page id=31
        self.assertEqual(set(salad_dressing_page.related_pages.all()), set([oil_page, vinegar_page]))

    def test_import_with_soft_dependency_on_grandchild(self):
        # https://github.com/wagtail/wagtail-transfer/issues/84 -
        # if there is a dependency loop with multiple hard dependencies and one soft dependency,
        # the soft dependency should be the one to be broken
        data = """{
            "ids_for_import": [
                ["wagtailcore.page", 10],
                ["wagtailcore.page", 11],
                ["wagtailcore.page", 12]
            ],
            "mappings": [
                ["wagtailcore.page", 10, "10101010-0000-0000-0000-000000000000"],
                ["wagtailcore.page", 11, "11111111-0000-0000-0000-000000000000"],
                ["wagtailcore.page", 12, "12121212-0000-0000-0000-000000000000"]
            ],
            "objects": [
                {
                    "model": "tests.pagewithrichtext",
                    "pk": 10,
                    "parent_id": 1,
                    "fields": {
                        "title": "002 Level 1 page",
                        "show_in_menus": false,
                        "live": true,
                        "slug": "level-1-page",
                        "body": "<p>link to <a id=\\"12\\" linktype=\\"page\\">level 3</a></p>",
                        "wagtail_admin_comments": []
                    }
                },
                {
                    "model": "tests.pagewithrichtext",
                    "pk": 11,
                    "parent_id": 10,
                    "fields": {
                        "title": "000 Level 2 page",
                        "show_in_menus": false,
                        "live": true,
                        "slug": "level-2-page",
                        "body": "<p>level 2</p>",
                        "wagtail_admin_comments": []
                    }
                },
                {
                    "model": "tests.pagewithrichtext",
                    "pk": 12,
                    "parent_id": 11,
                    "fields": {
                        "title": "001 Level 3 page",
                        "show_in_menus": false,
                        "live": true,
                        "slug": "level-3-page",
                        "body": "<p>level 3</p>",
                        "wagtail_admin_comments": []
                    }
                }
            ]
        }"""

        importer = ImportPlanner(root_page_source_pk=10, destination_parent_id=2)
        importer.add_json(data)
        # importer.run() will build a running order by iterating over the self.operations set.
        # Since the ordering of that set is non-deterministic, it may arrive at an ordering that
        # works by chance (i.e. at the point that it recognises the circular dependency, it is
        # looking at the soft dependency, which happens to be the correct one to break).
        # To prevent that, we'll hack importer.operations into a list, so that when importer.run()
        # iterates over it, it gets back a known 'worst case' ordering as defined by the page
        # titles.
        importer.operations = list(importer.operations)
        importer.operations.sort(key=lambda op: op.object_data['fields']['title'])

        importer.run()

        # all pages should be imported
        self.assertTrue(PageWithRichText.objects.filter(slug="level-1-page").exists())
        self.assertTrue(PageWithRichText.objects.filter(slug="level-2-page").exists())
        self.assertTrue(PageWithRichText.objects.filter(slug="level-3-page").exists())

        # link from homepage has to be broken
        page = PageWithRichText.objects.get(slug="level-1-page")
        self.assertEqual(page.body, '<p>link to level 3</p>')

    @mock.patch('requests.get')
    def test_import_custom_file_field(self, get):
        get.return_value.status_code = 200
        get.return_value.content = b'my test image file contents'

        data = """{
            "ids_for_import": [
                ["tests.avatar", 123]
            ],
            "mappings": [
                ["tests.avatar", 123, "01230123-0000-0000-0000-000000000000"]
            ],
            "objects": [
                {
                    "model": "tests.avatar",
                    "pk": 123,
                    "fields": {
                        "image": {
                            "download_url": "https://wagtail.io/media/original_images/muddy_waters.jpg",
                            "size": 18521,
                            "hash": "e4eab12cc50b6b9c619c9ddd20b61d8e6a961ada"
                        }
                    }
                }
            ]
        }"""

        importer = ImportPlanner(root_page_source_pk=1, destination_parent_id=None)
        importer.add_json(data)
        importer.run()

        # Check the db record and file was imported
        get.assert_called()
        avatar = Avatar.objects.get()
        self.assertEqual(avatar.image.read(), b'my test image file contents')

    def test_import_multi_table_model(self):
        # test that importing a model using multi table inheritance correctly imports the child model, not just the parent

        data = """{
            "ids_for_import": [
                ["tests.advert", 4]
            ],
            "mappings": [
                ["tests.advert", 4, "bfd3871a-048e-11eb-8000-287fcf66f689"]
            ],
            "objects": [
                {
                    "model": "tests.longadvert",
                    "pk": 4,
                    "fields": {
                        "slogan": "test",
                        "run_until": "2020-12-23T12:34:56Z",
                        "run_from": null,
                        "description": "longertest"
                    }
                }
            ]
        }"""

        importer = ImportPlanner(root_page_source_pk=1, destination_parent_id=None)
        importer.add_json(data)
        importer.run()

        imported_ad = LongAdvert.objects.filter(id=4).first()
        self.assertIsNotNone(imported_ad)
        self.assertEqual(imported_ad.slogan, "test")
        self.assertEqual(imported_ad.run_until, datetime(2020, 12, 23, 12, 34, 56, tzinfo=timezone.utc))
        self.assertEqual(imported_ad.description, "longertest")

    def test_import_model_with_generic_foreign_key(self):
        # test importing a model with a generic foreign key by importing a model that implements tagging using standard taggit (not ParentalKey)
        data = """{
            "ids_for_import": [["tests.advert", 4]],
            "mappings": [
                ["taggit.tag", 152, "ac92b2ba-0fa6-11eb-800b-287fcf66f689"],
                ["tests.advert", 4, "ac931726-0fa6-11eb-800c-287fcf66f689"],
                ["taggit.taggeditem", 150, "ac938e5a-0fa6-11eb-800d-287fcf66f689"]
            ],
            "objects": [
                {
                    "model": "tests.advert",
                    "pk": 4,
                    "fields": {"longadvert": null, "sponsoredpage": null, "slogan": "test",
                        "run_until": "2021-12-23T12:34:56Z", "run_from": null, "tags": "[<Tag: test_tag>]", "tagged_items": null}
                },
                {
                    "model": "taggit.taggeditem",
                    "pk": 150,
                    "fields": {"content_object": ["tests.advert", 4], "tag": 152}
                },
                {
                    "model": "taggit.tag",
                    "pk": 152,
                    "fields": {"name": "test_tag", "slug": "testtag"}
                }
            ]
        }"""

        importer = ImportPlanner(root_page_source_pk=1, destination_parent_id=None)
        importer.add_json(data)
        importer.run()

        imported_ad = Advert.objects.filter(id=4).first()
        self.assertIsNotNone(imported_ad)
        self.assertEqual(imported_ad.tags.first().name, "test_tag")

    def test_import_model_with_deleted_reverse_related_models(self):
        # test re-importing a model where WAGTAILTRANSFER_FOLLOWED_REVERSE_RELATIONS is used to track tag deletions
        # will delete tags correctly
        data = """{
            "ids_for_import": [["tests.advert", 4]],
            "mappings": [
                ["taggit.tag", 152, "ac92b2ba-0fa6-11eb-800b-287fcf66f689"],
                ["tests.advert", 4, "ac931726-0fa6-11eb-800c-287fcf66f689"],
                ["taggit.taggeditem", 150, "ac938e5a-0fa6-11eb-800d-287fcf66f689"]
            ],
            "objects": [
                {
                    "model": "tests.advert",
                    "pk": 4,
                    "fields": {"longadvert": null, "sponsoredpage": null, "slogan": "test",
                        "run_until": "2021-12-23T12:00:00Z", "run_from": null, "tags": "[<Tag: test_tag>]", "tagged_items": [150]}
                },
                {
                    "model": "taggit.taggeditem",
                    "pk": 150,
                    "fields": {"content_object": ["tests.advert", 4], "tag": 152}
                },
                {
                    "model": "taggit.tag",
                    "pk": 152,
                    "fields": {"name": "test_tag", "slug": "testtag"}
                }
            ]
        }"""

        importer = ImportPlanner(root_page_source_pk=1, destination_parent_id=None)
        importer.add_json(data)
        importer.run()

        imported_ad = Advert.objects.filter(id=4).first()
        self.assertIsNotNone(imported_ad)
        self.assertEqual(imported_ad.tags.first().name, "test_tag")

        data = """{
            "ids_for_import": [["tests.advert", 4]],
            "mappings": [
                ["tests.advert", 4, "ac931726-0fa6-11eb-800c-287fcf66f689"]
            ],
            "objects": [
                {
                    "model": "tests.advert",
                    "pk": 4,
                    "fields": {"longadvert": null, "sponsoredpage": null, "slogan": "test",
                        "run_until": "2021-12-23T12:00:00Z", "run_from": null, "tags": "[]", "tagged_items": []}
                }
            ]
        }"""

        importer = ImportPlanner(root_page_source_pk=1, destination_parent_id=None)
        importer.add_json(data)
        importer.run()

        imported_ad = Advert.objects.filter(id=4).first()
        self.assertIsNotNone(imported_ad)
        self.assertIsNone(imported_ad.tags.first())

    @override_settings(WAGTAILTRANSFER_FOLLOWED_REVERSE_RELATIONS=[('tests.advert', 'tagged_items', False)])
    def test_import_model_with_untracked_deleted_reverse_related_models(self):
        # test re-importing a model where WAGTAILTRANFER_FOLLOWED_REVERSE_RELATIONS is not used to track tag deletions
        # will not delete tags
        from wagtail_transfer import field_adapters
        importlib.reload(field_adapters)
        # force reload field adapters as followed/deleted variables are set on module load, so will not get new setting
        data = """{
            "ids_for_import": [["tests.advert", 4]],
            "mappings": [
                ["taggit.tag", 152, "ac92b2ba-0fa6-11eb-800b-287fcf66f689"],
                ["tests.advert", 4, "ac931726-0fa6-11eb-800c-287fcf66f689"],
                ["taggit.taggeditem", 150, "ac938e5a-0fa6-11eb-800d-287fcf66f689"]
            ],
            "objects": [
                {
                    "model": "tests.advert",
                    "pk": 4,
                    "fields": {"longadvert": null, "sponsoredpage": null, "slogan": "test",
                        "run_until": "2021-12-23T12:00:00Z", "run_from": null, "tags": "[<Tag: test_tag>]", "tagged_items": [150]}
                },
                {
                    "model": "taggit.taggeditem",
                    "pk": 150,
                    "fields": {"content_object": ["tests.advert", 4], "tag": 152}
                },
                {
                    "model": "taggit.tag",
                    "pk": 152,
                    "fields": {"name": "test_tag", "slug": "testtag"}
                }
            ]
        }"""

        importer = ImportPlanner(root_page_source_pk=1, destination_parent_id=None)
        importer.add_json(data)
        importer.run()

        imported_ad = Advert.objects.filter(id=4).first()
        self.assertIsNotNone(imported_ad)
        self.assertEqual(imported_ad.tags.first().name, "test_tag")

        data = """{
            "ids_for_import": [["tests.advert", 4]],
            "mappings": [
                ["tests.advert", 4, "ac931726-0fa6-11eb-800c-287fcf66f689"]
            ],
            "objects": [
                {
                    "model": "tests.advert",
                    "pk": 4,
                    "fields": {"longadvert": null, "sponsoredpage": null, "slogan": "test",
                            "run_until": "2021-12-23T12:00:00Z", "run_from": null, "tags": "[]", "tagged_items": []}
                }
            ]
        }"""

        importer = ImportPlanner(root_page_source_pk=1, destination_parent_id=None)
        importer.add_json(data)
        importer.run()

        imported_ad = Advert.objects.filter(id=4).first()
        self.assertIsNotNone(imported_ad)
        self.assertIsNotNone(imported_ad.tags.first())
