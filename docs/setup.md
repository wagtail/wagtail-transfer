#Setup

1. Clone the [Wagtail Transfer repository](https://github.com/wagtail/wagtail-transfer). 

2. In the terminal, navigate to the root of the cloned repository and run `pip install -e` .

3. Add `wagtail_transfer` to your project's `INSTALLED_APPS`.

4. In your project's top-level urls.py, add:

        from wagtail_transfer import urls as wagtailtransfer_urls
    
    and add:

        url(r'^wagtail-transfer/', include(wagtailtransfer_urls)),
    
    to the `urlpatterns` list above `include(wagtail_urls)`.
    
5. Add the settings `WAGTAILTRANSFER_SOURCES` and `WAGTAILTRANSFER_SECRET_KEY` to your project settings. 
    These are formatted as:

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
        
    However, it is best to store the `SECRET_KEY`s themselves in local environment variables for security.
        
    `WAGTAILTRANSFER_SOURCES` is a dictionary defining the sites available to import from, and their secret keys.

    `WAGTAILTRANSFER_SECRET_KEY` and the per-source `SECRET_KEY` settings are used to authenticate the communication between the 
    source and destination instances; this prevents unauthorised users from using this API to retrieve sensitive data such 
    as password hashes. The `SECRET_KEY` for each entry in `WAGTAILTRANSFER_SOURCES` must match that instance's 
    `WAGTAILTRANSFER_SECRET_KEY`.
    
Once you've followed these instructions for all your source and destination sites, you can start 
[importing content](basic_usage.md). 

If you need additional configuration - you want to configure which referenced models are updated, how models are identified 
between Wagtail instances, or which models are pulled in and imported from references on an imported page, you can
check out [how mappings and references work](how_it_works.md) and the [settings reference](settings.md).

