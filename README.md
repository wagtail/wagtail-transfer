# Wagtail Transfer

<img alt="Wagtail Transfer logo with two facing wagtails" src="docs/img/wagtail_transfer_logo.svg" height="25%" width="25%">

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
