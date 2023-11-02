# Wagtail Transfer

<img alt="Wagtail Transfer logo with two facing wagtails" src="docs/img/wagtail_transfer_logo.svg" height="25%" width="25%">

An extension for Wagtail allowing content to be transferred between multiple instances of a Wagtail project

RFC: https://github.com/wagtail/rfcs/pull/42

Developed by [Torchbox](https://torchbox.com/) and sponsored by [The Motley Fool](https://www.fool.com/).


## Installation

* Install the package with `pip install wagtail-transfer`
* Add `'wagtail_transfer'` to your project's `INSTALLED_APPS`
* In your project's top-level urls.py, add:

      from wagtail_transfer import urls as wagtailtransfer_urls

  and place

      path('wagtail-transfer/', include(wagtailtransfer_urls)),

  into the urlpatterns list, above the `include(wagtail_urls)` line.

* Add the settings `WAGTAILTRANSFER_SOURCES` and `WAGTAILTRANSFER_SECRET_KEY` to your project settings. For example:

      WAGTAILTRANSFER_SOURCES = {
          'staging': {
              'BASE_URL': 'https://staging.example.com/wagtail-transfer/',
              'SECRET_KEY': '4ac4822149691395773b2a8942e1a472',
          },
          'production': {
              'BASE_URL': 'https://www.example.com/wagtail-transfer/',
              'SECRET_KEY': 'a36476ffc6af34dc935570d97369eca0',
          },
      }

      WAGTAILTRANSFER_SECRET_KEY = '7cd5de8229be75e1e0c2af8abc2ada7e'

  `WAGTAILTRANSFER_SOURCES` is a dict defining the sites available to import from.

  `WAGTAILTRANSFER_SECRET_KEY` and the per-source `SECRET_KEY` settings are used to authenticate the communication between the source and destination instances; this prevents unauthorised users from using this API to retrieve sensitive data such as password hashes. The `SECRET_KEY` for each entry in `WAGTAILTRANSFER_SOURCES` must match that instance's `WAGTAILTRANSFER_SECRET_KEY`.

* Create a user group (Wagtail admin > Settings > Groups > Add a group) with the permission "Can import pages and snippets from other sites". The "Import" menu item, and the associated import views, will only be available to members of this group (and superusers).

## Configuration

The following settings are additionally recognised:

* `WAGTAILTRANSFER_UPDATE_RELATED_MODELS = ['wagtailimages.image', 'adverts.advert']`

  Specifies a list of models that, whenever we encounter references to them in imported content, should be updated to the latest version from the source site as part of the import.

  Whenever an object being imported contains a reference to a related object (through a ForeignKey, RichTextField or StreamField), the 'importance' of that related object will tend to vary according to its type. For example, a reference to an Image object within a page usually means that the image will be shown on that page; in this case, the Image model is sufficiently important to the imported page that we want the importer to not only ensure that image exists at the destination, but is updated to its newest version as well. Contrast this with the example of an 'author' snippet attached to blog posts, containing various fields of data about that person (e.g. bio, social media links); in this case, the author information is not really part of the blog post, and it's not expected that we would update it when running an import of blog posts.

* `WAGTAILTRANSFER_LOOKUP_FIELDS = {'blog.author': ['first_name', 'surname']}`

  Specifies a list of fields to use for object lookups on the given models.

  Normally, imported objects will be assigned a random UUID known across all sites, so that those objects can be recognised on subsequent imports and be updated rather than creating a duplicate. This behaviour is less useful for models that already have a uniquely identifying field, or set of fields, such as an author identified by first name and surname - if the same author exists on the source and destination site, but this was not the result of a previous import, then the UUID-based matching will consider them distinct, and attempt to create a duplicate author record at the destination. Adding an entry in `WAGTAILTRANSFER_LOOKUP_FIELDS` will mean that any imported instances of the given model will be looked up based on the specified fields, rather than by UUID.

* `WAGTAILTRANSFER_NO_FOLLOW_MODELS = ['wagtailcore.page', 'organisations.Company']`

  Specifies a list of models that should not be imported by association when they are referenced from imported content. Defaults to `['wagtailcore.page']`.

  By default, objects referenced within imported content will be recursively imported to ensure that those references are still valid on the destination site. However, this is not always desirable - for example, if this happened for the Page model, this would imply that any pages linked from an imported page would get imported as well, along with any pages linked from _those_ pages, and so on, leading to an unpredictable number of extra pages being added anywhere in the page tree as a side-effect of the import. Models listed in `WAGTAILTRANSFER_NO_FOLLOW_MODELS` will thus be skipped in this process, leaving the reference unresolved. The effect this has on the referencing page will vary according to the kind of relation: nullable foreign keys, one-to-many and many-to-many relations will simply omit the missing object; references in rich text and StreamField will become broken links (just as linking a page and then deleting it would); while non-nullable foreign keys will prevent the object from being created at all (meaning that any objects referencing _that_ object will end up with unresolved references, to be handled by the same set of rules).

* `WAGTAILTRANSFER_FOLLOWED_REVERSE_RELATIONS = [('wagtailimages.image', 'tagged_items', True)]`

  Specifies a list of models, their reverse relations to follow, and whether deletions should be synced, when identifying object references that should be imported to the destination site. Defaults to `[('wagtailimages.image', 'tagged_items', True)]`.

  By default, Wagtail Transfer will not follow reverse relations (other than importing child models of `ClusterableModel` subclasses) when identifying referenced models. Specifying a `(model, reverse_relationship_name, track_deletions)` in `WAGTAILTRANSFER_FOLLOWED_REVERSE_RELATIONS` means that when
  encountering that model and relation, Wagtail Transfer will follow the reverse relationship from the specified model and add the models found to the import if they do not exist on the destination site. This is typically useful in cases such as tags on non-Page models. The `track_deletions` boolean,
  if `True`, will delete any models in the reverse relation on the destination site that do not exist in the source site's reverse relation. As a result,
  it should only be used for models that behave strictly like child models but do not use `ParentalKey` - for example, tags, where importing an image with deleted tags should delete those tag linking models on the destination site as well.

  Note: describing the relationship according to the format expected is important. An import may still complete succesfully if you've added a value that doesn't match, in which case the followed relation simply won't be updated and may cause unexpected problems on future imports. 
  
  For example, if you happen to also be using the `wagtail-personalisation` library on your project, you'll need to make sure you account for page variants: 
  ```python
  WAGTAILTRANSFER_FOLLOWED_REVERSE_RELATIONS = [
    ('wagtailcore.page', 'personalisable_canonical_metadata', True),
  ]
  ```


Note that these settings do not accept models that are defined as subclasses through [multi-table inheritance](https://docs.djangoproject.com/en/stable/topics/db/models/#multi-table-inheritance) - in particular, they cannot be used to define behaviour that only applies to specific subclasses of Page.

* `WAGTAILTRANSFER_CHOOSER_API_PROXY_TIMEOUT = 5`

  By default, each API call made to browse the page tree on the source server has a timeout limit of 5 seconds. If you find this threshold is too low, you can increase it. This may be of particular use if you are running two local runservers to test or extend Wagtail Transfer.

## Management commands

    ./manage.py preseed_transfer_table [--range=MIN-MAX] model_or_app [model_or_app ...]

Populates the table of UUIDs with known predictable values for the given model(s) and ID range. Effectively, running this command informs wagtail-transfer that all objects in the given set can be trusted not to have IDs that collide with other objects, so that when the same ID is encountered on another site instance, it is known to refer to the same object and will be handled as an update rather than a creation. This is useful in situations where databases have been copied between installations without the involvement of wagtail-transfer.

`model_or_app` can be either an individual model name such as `wagtailcore.page` or an app label such as `wagtaildocs`; in the latter case, all models in the app will be assigned UUIDs. Note that when multi-table inheritance is in use, only the base model is assigned a UUID; for page models, this means that `preseed_transfer_table` only needs to run on `wagtailcore.page`, not specific page types. However, related models linked through `ParentalKey` and `InlinePanel` do still need their own UUIDs.

The following command should be sufficient to cover all of the relevant models that are provided as standard by Django and Wagtail:

    ./manage.py preseed_transfer_table auth wagtailcore wagtailimages.image wagtaildocs

### Example 1: launching a site with wagtail-transfer in place

Suppose a site has been developed and populated with content on a staging environment at staging.example.com. We intend to launch this site at live.example.com, and plan to continue using staging.example.com to prepare content in advance of transferring it to the live site. Whenever these transfers include pages that existed prior to launch, we want to ensure that the existing pages are updated rather than creating duplicates. This can be done as follows:

 * Install wagtail-transfer on your project
 * Deploy the codebase to live.example.com
 * On staging.example.com, run: `./manage.py preseed_transfer_table wagtailcore.page`
 * Dump the database from staging.example.com and restore it on live.example.com

live.example.com now has a table of UUIDs matching the table on staging.example.com, and so any future transfers involving currently-existing pages will treat those as updates rather than creations.

### Example 2: retrospectively installing wagtail-transfer on an existing pair of sites

Suppose a site has been developed and populated with content on a staging environment at staging.example.com and launched at live.example.com, and subsequently both site instances have continued to receive edits. We now wish to roll out wagtail-transfer, while ensuring that the pages common to both instances are handled correctly. Comparing both instances, we find that the common pages have IDs 1 to 199 inclusive, and IDs above 199 refer to different pages between the instances. We proceed as follows:

 * Install wagtail-transfer on your project
 * Deploy to both staging.example.com and live.example.com
 * On both instances, run: `./manage.py preseed_transfer_table wagtailcore.page --range=1-199`

 The `preseed_transfer_table` command generates consistent UUIDs between the two site instances, so any transfers involving this ID range will recognise the pages as matching, and handle them as updates rather than creations.
