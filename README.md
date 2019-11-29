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

* Add a `WAGTAILTRANSFER_SOURCES` setting to your project settings. This is a dict defining the sites available to import from, for example:

      WAGTAILTRANSFER_SOURCES = {
          'staging': {
              'CHOOSER_API': 'https://staging.example.com/wagtail-transfer/api/chooser/pages/',
          },
          'production': {
              'CHOOSER_API': 'https://www.example.com/wagtail-transfer/api/chooser/pages/',
          },
      }
