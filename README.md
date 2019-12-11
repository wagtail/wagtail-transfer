# wagtail-transfer

An extension for Wagtail allowing content to be transferred between multiple instances of a Wagtail project

RFC: https://github.com/wagtail/rfcs/pull/42


## Installation

* Check out this repository and run `pip install -e .` from the root
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
