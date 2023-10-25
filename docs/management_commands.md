# Management commands

    ./manage.py preseed_transfer_table [--range=MIN-MAX] model_or_app [model_or_app ...]

Populates the table of UUIDs with known predictable values for the given model(s) and ID range. Effectively, running this command informs wagtail-transfer that all objects in the given set can be trusted not to have IDs that collide with other objects, so that when the same ID is encountered on another site instance, it is known to refer to the same object and will be handled as an update rather than a creation. This is useful in situations where databases have been copied between installations without the involvement of wagtail-transfer.

`model_or_app` can be either an individual model name such as `wagtailcore.page` or an app label such as `wagtaildocs`; in the latter case, all models in the app will be assigned UUIDs. Note that when multi-table inheritance is in use, only the base model is assigned a UUID; for page models, this means that `preseed_transfer_table` only needs to run on `wagtailcore.page`, not specific page types. However, related models linked through `ParentalKey` and `InlinePanel` do still need their own UUIDs.

The following command should be sufficient to cover all of the relevant models that are provided as standard by Django and Wagtail:

    ./manage.py preseed_transfer_table auth wagtailcore wagtailimages.image wagtaildocs

## Example 1: launching a site with wagtail-transfer in place

Suppose a site has been developed and populated with content on a staging environment at staging.example.com. We intend to launch this site at live.example.com, and plan to continue using staging.example.com to prepare content in advance of transferring it to the live site. Whenever these transfers include pages that existed prior to launch, we want to ensure that the existing pages are updated rather than creating duplicates. This can be done as follows:

 * Install wagtail-transfer on your project
 * Deploy the codebase to live.example.com
 * On staging.example.com, run: `./manage.py preseed_transfer_table wagtailcore.page`
 * Dump the database from staging.example.com and restore it on live.example.com

live.example.com now has a table of UUIDs matching the table on staging.example.com, and so any future transfers involving currently-existing pages will treat those as updates rather than creations.

## Example 2: retrospectively installing wagtail-transfer on an existing pair of sites

Suppose a site has been developed and populated with content on a staging environment at staging.example.com and launched at live.example.com, and subsequently both site instances have continued to receive edits. We now wish to roll out wagtail-transfer, while ensuring that the pages common to both instances are handled correctly. Comparing both instances, we find that the common pages have IDs 1 to 199 inclusive, and IDs above 199 refer to different pages between the instances. We proceed as follows:

 * Install wagtail-transfer on your project
 * Deploy to both staging.example.com and live.example.com
 * On both instances, run: `./manage.py preseed_transfer_table wagtailcore.page --range=1-199`

 The `preseed_transfer_table` command generates consistent UUIDs between the two site instances, so any transfers involving this ID range will recognise the pages as matching, and handle them as updates rather than creations.
