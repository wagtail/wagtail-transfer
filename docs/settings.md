# Settings and Hooks

## Settings

### `WAGTAILTRANSFER_SECRET_KEY`

```python
WAGTAILTRANSFER_SECRET_KEY = '7cd5de8229be75e1e0c2af8abc2ada7e'
```

The secret key used to authenticate requests to import content from this site to another. The secret key in the 
matching part of the importing site's `WAGTAILTRANSFER_SOURCES` must be identical, or the transfer will be rejected - 
this prevents unauthorised import of sensitive data. 

### `WAGTAILTRANSFER_SOURCES`

```python
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
```

A dictionary defining the sites available to import from, and their secret keys.

### `WAGTAILTRANSFER_UPDATE_RELATED_MODELS`

```python
WAGTAILTRANSFER_UPDATE_RELATED_MODELS = ['wagtailimages.image', 'adverts.advert']
```

Specifies a list of models that, whenever we encounter references to them in imported content, should be updated to the 
latest version from the source site as part of the import.

Whenever an object being imported contains a reference to a related object (through a ForeignKey, RichTextField or 
StreamField), the 'importance' of that related object will tend to vary according to its type. For example, a reference 
to an Image object within a page usually means that the image will be shown on that page; in this case, the Image model 
is sufficiently important to the imported page that we want the importer to not only ensure that image exists at the 
destination, but is updated to its newest version as well. Contrast this with the example of an 'author' snippet 
attached to blog posts, containing various fields of data about that person (e.g. bio, social media links); in this 
case, the author information is not really part of the blog post, and it's not expected that we would update it when 
running an import of blog posts.

### `WAGTAILTRANSFER_LOOKUP_FIELDS`

```python
WAGTAILTRANSFER_LOOKUP_FIELDS = {'blog.author': ['first_name', 'surname']}
```

Specifies a list of fields to use for object lookups on the given models.

Normally, imported objects will be assigned a random UUID known across all sites, so that those objects can be 
recognised on subsequent imports and be updated rather than creating a duplicate. This behaviour is less useful for 
models that already have a uniquely identifying field, or set of fields, such as an author identified by first name 
and surname - if the same author exists on the source and destination site, but this was not the result of a previous 
import, then the UUID-based matching will consider them distinct, and attempt to create a duplicate author record at the 
destination. Adding an entry in WAGTAILTRANSFER_LOOKUP_FIELDS will mean that any imported instances of the given model 
will be looked up based on the specified fields, rather than by UUID.

The default value for `WAGTAILTRANSFER_LOOKUP_FIELDS` is:

```python
{
    'taggit.tag': ['slug'],
    'wagtailcore.locale': ["language_code"],
    'contenttypes.contenttype': ['app_label', 'model'],
}
```

Overriding these values may result in issues as described above, particularly in the case of `ContentType`.

### `WAGTAILTRANSFER_NO_FOLLOW_MODELS`

```python
WAGTAILTRANSFER_NO_FOLLOW_MODELS = ['wagtailcore.page', 'organisations.Company']
```

Specifies a list of models that should not be imported by association when they are referenced from imported content. 
Defaults to `['wagtailcore.page', 'contenttypes.contenttype']`.

By default, objects referenced within imported content will be recursively imported to ensure that those references are 
still valid on the destination site. However, this is not always desirable - for example, if this happened for the Page 
model, this would imply that any pages linked from an imported page would get imported as well, along with any pages 
linked from those pages, and so on, leading to an unpredictable number of extra pages being added anywhere in the page 
tree as a side-effect of the import. Models listed in WAGTAILTRANSFER_NO_FOLLOW_MODELS will thus be skipped in this 
process, leaving the reference unresolved. The effect this has on the referencing page will vary according to the kind 
of relation: nullable foreign keys, one-to-many and many-to-many relations will simply omit the missing object; 
references in rich text and StreamField will become broken links (just as linking a page and then deleting it would); 
while non-nullable foreign keys will prevent the object from being created at all (meaning that any objects referencing 
that object will end up with unresolved references, to be handled by the same set of rules).

Note that these settings do not accept models that are defined as subclasses through multi-table inheritance - in 
particular, they cannot be used to define behaviour that only applies to specific subclasses of Page.


### `WAGTAILTRANSFER_FOLLOWED_REVERSE_RELATIONS`

```python
WAGTAILTRANSFER_FOLLOWED_REVERSE_RELATIONS = [('wagtailimages.image', 'tagged_items', True)]
```

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

### `WAGTAILTRANSFER_CHOOSER_API_PROXY_TIMEOUT`

```python
WAGTAILTRANSFER_CHOOSER_API_PROXY_TIMEOUT = 5
```

  By default, each API call made to browse the page tree on the source server has a timeout limit of 5 seconds. If you find this threshold is too low, you can increase it. This may be of particular use if you are running two local runservers to test or extend Wagtail Transfer.


## Hooks

### `register_field_adapters`

Field adapters are classes used by Wagtail Transfer to serialize and identify references from fields when exporting,
and repopulate them with the serialised data when importing. You can register a custom field adapter by using the
`register_field_adapters` hook. A function registered with this hook should return a dictionary which maps field classes
to field adapter classes (note that with inheritance, the field adapter registered with the closest ancestor class will be used).
For example, to register a custom field adapter against Django's `models.Field`:

```python
# <my_app>/wagtail_hooks.py

from django.db import models

from wagtail import hooks
from wagtail_transfer.field_adapters import FieldAdapter


class MyCustomAdapter(FieldAdapter):
    pass


@hooks.register('register_field_adapters')
def register_my_custom_adapter():
    return {models.Field: MyCustomAdapter}

```


### `register_custom_serializers`

In exceptional cases, such as limiting the fields you export to only a subset of the content, you may need to use a custom serializer instead of the default `PageSerializer`.
You can register a custom serializer by using the `register_custom_serializers` hook.
A function registered with this hook should return a dictionary which maps model classes to serializer classes (note that with inheritance, the serializer registered with the closest ancestor class will be used).
For example, to register a custom serializer against `myapp.MyModel`:

```python
# <my_app>/wagtail_hooks.py


from wagtail import hooks
from wagtail_transfer.serializers import PageSerializer

from myapp.models import MyModel

class MyModelCustomSerializer(PageSerializer):

    ignored_fields = PageSerializer.ignored_fields + [
        'secret_field_1',
        'environment_specific_data_field_123',
        ...
    ]
    pass


@hooks.register('register_custom_serializers')
def register_my_custom_serializer():
    return {MyModel: MyModelCustomSerializer}

```
