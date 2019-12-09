from unittest import mock

from django.contrib.contenttypes.models import ContentType
from django.test import TestCase
from wagtail.core.models import Collection
from wagtail.images.models import Image

from wagtail_transfer.models import IDMapping
from wagtail_transfer.operations import ImportPlanner
from tests.models import PageWithRichText, PageWithStreamField, SectionedPage, SimplePage, SponsoredPage


class TestImport(TestCase):
    fixtures = ['test.json']

    def test_import_pages(self):
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
                        "intro": "This page is imported from the source site"
                    }
                },
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
                }
            ]
        }"""

        importer = ImportPlanner(12, None)
        importer.add_json(data)
        importer.run()

        updated_page = SimplePage.objects.get(url_path='/home/')
        self.assertEqual(updated_page.intro, "This is the updated homepage")

        created_page = SimplePage.objects.get(url_path='/home/imported-child-page/')
        self.assertEqual(created_page.intro, "This page is imported from the source site")

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
                        "intro": "yay fossil fuels and climate change"
                    }
                },
                {
                    "model": "tests.advert",
                    "pk": 11,
                    "fields": {
                        "slogan": "put a leopard in your tank"
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
                        "intro": "you can make cakes with them"
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

        importer = ImportPlanner(12, None)
        importer.add_json(data)
        importer.run()

        updated_page = SponsoredPage.objects.get(url_path='/home/oil-is-still-great/')
        self.assertEqual(updated_page.intro, "yay fossil fuels and climate change")
        self.assertEqual(updated_page.advert.slogan, "put a leopard in your tank")

        created_page = SponsoredPage.objects.get(url_path='/home/eggs-are-great-too/')
        self.assertEqual(created_page.intro, "you can make cakes with them")
        self.assertEqual(created_page.advert.slogan, "go to work on an egg")

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
                        "sections": [
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
                    }
                }
            ]
        }"""

        importer = ImportPlanner(100, 2)
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
                        "sections": [
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
                    }
                }
            ]
        }"""

        importer = ImportPlanner(100, 2)
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
                        "body": "<p>But I have a <a id=\\"12\\" linktype=\\"page\\">link</a></p>"
                    }
                }
            ]
        }"""

        importer = ImportPlanner(1, None)
        importer.add_json(data)
        importer.run()

        page = PageWithRichText.objects.get(slug="imported-rich-text-page")

        # tests that a page link id is changed successfully when imported
        self.assertEqual(page.body, '<p>But I have a <a id="1" linktype="page">link</a></p>')

        # TODO: this should include an embed type as well once document/image import is added

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
                            "search_description": "",
                            "body": "[{\\"type\\": \\"link_block\\", \\"value\\": {\\"page\\": 100, \\"text\\": \\"Test\\"}, \\"id\\": \\"fc3b0d3d-d316-4271-9e31-84919558188a\\"}, {\\"type\\": \\"page\\", \\"value\\": 200, \\"id\\": \\"c6d07d3a-72d4-445e-8fa5-b34107291176\\"}, {\\"type\\": \\"stream\\", \\"value\\": [{\\"type\\": \\"page\\", \\"value\\": 300, \\"id\\": \\"8c0d7de7-4f77-4477-be67-7d990d0bfb82\\"}], \\"id\\": \\"21ffe52a-c0fc-4ecc-92f1-17b356c9cc94\\"}, {\\"type\\": \\"list_of_pages\\", \\"value\\": [500], \\"id\\": \\"17b972cb-a952-4940-87e2-e4eb00703997\\"}]"},
                            "parent_id": 300
                        }
                    ]
                }"""
        importer = ImportPlanner(1, None)
        importer.add_json(data)
        importer.run()

        page = PageWithStreamField.objects.get(slug="i-have-a-streamfield")

        imported_streamfield = page.body.stream_block.get_prep_value(page.body)

        # Check that PageChooserBlock ids are converted correctly to those on the destination site
        self.assertEqual(imported_streamfield, [{'type': 'link_block', 'value': {'page': 1, 'text': 'Test'}, 'id': 'fc3b0d3d-d316-4271-9e31-84919558188a'}, {'type': 'page', 'value': 2, 'id': 'c6d07d3a-72d4-445e-8fa5-b34107291176'}, {'type': 'stream', 'value': [{'type': 'page', 'value': 3, 'id': '8c0d7de7-4f77-4477-be67-7d990d0bfb82'}], 'id': '21ffe52a-c0fc-4ecc-92f1-17b356c9cc94'}, {'type': 'list_of_pages', 'value': [5], 'id': '17b972cb-a952-4940-87e2-e4eb00703997'}])

    def test_import_page_with_streamfield_rich_text_block(self):
        # Check that ids in RichTextBlock within a StreamField are converted properly

        data = """{"ids_for_import": [["wagtailcore.page", 6]], "mappings": [["wagtailcore.page", 6, "a231303a-1754-11ea-8000-0800278dc04d"], ["wagtailcore.page", 100, "11111111-1111-1111-1111-111111111111"]], "objects": [{"model": "tests.pagewithstreamfield", "pk": 6, "fields": {"title": "My streamfield rich text block has a link", "slug": "my-streamfield-rich-text-block-has-a-link", "live": true, "seo_title": "", "show_in_menus": false, "search_description": "", "body": "[{\\"type\\": \\"rich_text\\", \\"value\\": \\"<p>I link to a <a id=\\\\\\"100\\\\\\" linktype=\\\\\\"page\\\\\\">page</a>.</p>\\", \\"id\\": \\"7d4ee3d4-9213-4319-b984-45be4ded8853\\"}]"}, "parent_id": 100}]}"""
        importer = ImportPlanner(1, None)
        importer.add_json(data)
        importer.run()

        page = PageWithStreamField.objects.get(slug="my-streamfield-rich-text-block-has-a-link")

        imported_streamfield = page.body.stream_block.get_prep_value(page.body)

        self.assertEqual(imported_streamfield, [{'type': 'rich_text', 'value': '<p>I link to a <a id="1" linktype="page">page</a>.</p>', 'id': '7d4ee3d4-9213-4319-b984-45be4ded8853'}])

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
                        "tagged_items": "[]"
                    }
                }
            ]
        }"""

        importer = ImportPlanner(1, None)
        importer.add_json(data)
        importer.run()

        # Check the image was imported
        image = Image.objects.get()
        self.assertEqual(image.title, "Lightnin' Hopkins")
        self.assertEqual(image.file.read(), b'my test image file contents')

        # TODO: We should verify these
        self.assertEqual(image.file_size, 18521)
        self.assertEqual(image.file_hash, "e4eab12cc50b6b9c619c9ddd20b61d8e6a961ada")

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

        importer = ImportPlanner(1, None)
        importer.add_json(data)
        importer.run()

        # Check the new collection was imported
        collection = Collection.objects.get(name="New collection")
        self.assertEqual(collection.get_parent(), root_collection)
