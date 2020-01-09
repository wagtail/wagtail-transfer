# wagtail-transfer

An extension for Wagtail allowing content to be transferred between multiple instances of a Wagtail project

RFC: https://github.com/wagtail/rfcs/pull/42


## Installation

* Install the package with `pip install wagtail-transfer`
* Add `'wagtail_transfer'` to your project's `INSTALLED_APPS`
* In your project's top-level urls.py, add:

      from wagtail_transfer import urls as wagtailtransfer_urls

  and place

      url(r'^wagtail-transfer/', include(wagtailtransfer_urls)),

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

Note that these settings do not accept models that are defined as subclasses through [multi-table inheritance](https://docs.djangoproject.com/en/stable/topics/db/models/#multi-table-inheritance) - in particular, they cannot be used to define behaviour that only applies to specific subclasses of Page.
