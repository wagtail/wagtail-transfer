import logging
import json
import pathlib
from functools import lru_cache
from urllib.parse import urlparse

from django.conf import settings
from django.contrib.contenttypes.fields import (GenericForeignKey,
                                                GenericRelation)
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ImproperlyConfigured
from django.db import models
from django.db.models.fields.reverse_related import ManyToOneRel
from django.utils.encoding import is_protected_type
from django.utils.functional import cached_property
from modelcluster.fields import ParentalKey
from taggit.managers import TaggableManager
from wagtail import hooks
from wagtail.fields import RichTextField, StreamField

from .files import File, FileTransferError, get_file_hash, get_file_size
from .locators import get_locator_for_model
from .models import get_base_model, get_base_model_for_path
from .richtext import get_reference_handler
from .streamfield import get_object_references, update_object_ids


logger = logging.getLogger(__name__)

WAGTAILTRANSFER_FOLLOWED_REVERSE_RELATIONS = getattr(settings, "WAGTAILTRANSFER_FOLLOWED_REVERSE_RELATIONS", [('wagtailimages.image', 'tagged_items', True)])
FOLLOWED_REVERSE_RELATIONS = {
    (model_label.lower(), relation.lower()) for model_label, relation, _ in WAGTAILTRANSFER_FOLLOWED_REVERSE_RELATIONS
}
DELETED_REVERSE_RELATIONS = {
    (model_label.lower(), relation.lower()) for model_label, relation, track_deletions in WAGTAILTRANSFER_FOLLOWED_REVERSE_RELATIONS if track_deletions
}
ADMIN_BASE_URL = getattr(
    settings, "WAGTAILADMIN_BASE_URL",
    getattr(settings, "BASE_URL", None)
)


class FieldAdapter:
    def __init__(self, field):
        self.field = field
        self.name = self.field.name

    def serialize(self, instance):
        """
        Retrieve the value for this field from the given model instance, and return a
        representation of it that can be included in JSON data
        """
        value = self.field.value_from_object(instance)
        if not is_protected_type(value):
            value = self.field.value_to_string(instance)

        return value

    def get_object_references(self, instance):
        """
        Return a set of (model_class, id) pairs for all objects referenced in this field
        """
        return set()

    def get_dependencies(self, value):
        """
        A set of (base_model_class, id, is_hard) tuples for objects that must exist at the
        destination before populate_field can proceed with the given value.

        is_hard is a boolean - if True, then the object MUST exist in order for populate_field to
            succeed; if False, then the operation can still complete without it (albeit possibly
            with broken links).

        This differs from get_object_references in that references inside related child objects
        do not need to be considered, as they do not block the creation/update of the parent
        object.
        """
        return set()

    def get_object_deletions(self, instance, value, context):
        """
        A set of (base_model_class, id) tuples for objects that must be deleted at the destination site
        """
        return set()

    def update_object_references(self, value, destination_ids_by_source):
        """
        Return a modified version of value with object references replaced by their corresponding
        entries in destination_ids_by_source - a mapping of (model_class, source_id) to
        destination_id
        """
        return value

    def populate_field(self, instance, value, context):
        """
        Populate this field on the passed model instance, given a value in its serialized form
        as returned by `serialize`
        """
        value = self.update_object_references(value, context.destination_ids_by_source)
        setattr(instance, self.field.get_attname(), self.field.to_python(value))

    def get_managed_fields(self):
        """
        Normally, a FieldAdapter will adapt a single field. However, more complex fields like
        GenericForeignKey may 'manage' several other fields. get_managed_fields returns a list of names
        of managed fields, whose field adapters should not be used when serializing the model. Note
        that if a managed field also has managed fields itself, these will also be ignored when
        serializing the model - the current field adapter is expected to address all managed fields in
        the chain.
        """
        return []

    def get_objects_to_serialize(self, instance):
        """
        Return a set of (model_class, id) pairs for objects that should be serialized on export, before
        it is known whether or not they exist or should be updated at the destination site
        """
        return set()



class ForeignKeyAdapter(FieldAdapter):
    def __init__(self, field):
        super().__init__(field)
        self.related_base_model = get_base_model(self.field.related_model)

    def get_object_references(self, instance):
        pk = self.field.value_from_object(instance)
        if pk is None:
            return set()
        else:
            return {(self.related_base_model, pk)}

    def get_dependencies(self, value):
        if value is None:
            return set()
        elif self.field.blank and self.field.null:
            # field is nullable, so it's a soft dependency; we can leave the field empty in the
            # case that the target object cannot be created
            return {(self.related_base_model, value, False)}
        else:
            # this is a hard dependency
            return {(self.related_base_model, value, True)}

    def update_object_references(self, value, destination_ids_by_source):
        return destination_ids_by_source.get((self.related_base_model, value))


class GenericForeignKeyAdapter(FieldAdapter):
    def serialize(self, instance):
        linked_instance = getattr(instance, self.field.name, None)
        if linked_instance:
            # here we do not use the base model, as the GFK could be pointing specifically at the child
            # which needs to be represented accurately
            return (linked_instance._meta.label_lower, linked_instance.pk)

    def get_object_references(self, instance):
        linked_instance = getattr(instance, self.field.name, None)
        if linked_instance:
            return {(get_base_model(linked_instance), linked_instance.pk)}
        return set()

    def get_dependencies(self, value):
        if value is None:
            return set()

        model_path, model_id = value
        base_model = get_base_model_for_path(model_path)

        # GenericForeignKey itself has no blank or null properties, so we need to determine its nullable status
        # from the underlying fields it uses
        options = self.field.model._meta
        ct_field = options.get_field(self.field.ct_field)
        fk_field = options.get_field(self.field.ct_field)

        if all((ct_field.blank, ct_field.null, fk_field.blank, fk_field.null)):
            # field is nullable, so it's a soft dependency; we can leave the field empty in the
            # case that the target object cannot be created
            return {(base_model, model_id, False)}
        else:
            # this is a hard dependency
            return {(base_model, model_id, True)}

    def update_object_references(self, value, destination_ids_by_source):
        if value:
            model_path, model_id = value
            base_model = get_base_model_for_path(model_path)
            return (model_path, destination_ids_by_source.get((base_model, model_id)))

    def populate_field(self, instance, value, context):
        model_id, content_type = None, None
        if value:
            model_path, model_id = self.update_object_references(value, context.destination_ids_by_source)
            content_type = ContentType.objects.get_by_natural_key(*model_path.split('.'))

        setattr(instance, instance._meta.get_field(self.field.ct_field).get_attname(), content_type.pk)
        setattr(instance, self.field.fk_field, model_id)

    def get_managed_fields(self):
        return [self.field.fk_field, self.field.ct_field]


class ManyToOneRelAdapter(FieldAdapter):
    def __init__(self, field):
        super().__init__(field)
        self.related_field = getattr(field, 'field', None) or getattr(field, 'remote_field', None)
        self.related_base_model = get_base_model(field.related_model)
        self.is_parental = isinstance(self.related_field, ParentalKey)
        self.is_followed = (get_base_model(self.field.model)._meta.label_lower, self.name) in FOLLOWED_REVERSE_RELATIONS
        if self.is_parental or self.is_followed:
            # presumably this info is most useful when it's going to be used, so this avoids some extra log noise
            logger.debug("Field adaptor registered: "
                         f"{self.field}, {get_base_model(self.field.model)._meta.label_lower, self.name})")

    def _get_related_objects(self, instance):
        results = getattr(instance, self.name).all()
        if results:
            logger.debug("Related objects found for "
                         f"{self.name}, {instance}: {results}")
        else:
            logger.debug(f"No related objects found for {self.name}")
        return results

    def serialize(self, instance):
        if self.is_parental or self.is_followed:
            return list(self._get_related_objects(instance).values_list('pk', flat=True))

    def get_object_references(self, instance):
        refs = set()
        if self.is_parental or self.is_followed:
            for pk in self._get_related_objects(instance).values_list('pk', flat=True):
                refs.add((self.related_base_model, pk))
        else:
            logger.debug(f"{self.field}, {get_base_model(self.field.model)._meta.label_lower, self.name}"
                         " is not parental or followed, not adding to refs")
        return refs

    def get_object_deletions(self, instance, value, context):
        if (self.is_parental or (get_base_model(self.field.model)._meta.label_lower, self.name) in DELETED_REVERSE_RELATIONS):
            value = value or []
            uids = {context.uids_by_source[(self.related_base_model, pk)] for pk in value}
            # delete any related objects on the existing object if they can't be mapped back
            # to one of the uids in the new set
            locator = get_locator_for_model(self.related_base_model)
            matched_destination_ids = set()
            for uid in uids:
                child = locator.find(uid)
                if child is not None:
                    matched_destination_ids.add(child.pk)
            logger.debug(f"Deleting the following objects: {matched_destination_ids}")
            return {child for child in self._get_related_objects(instance) if child.pk not in matched_destination_ids}
        return set()

    def get_objects_to_serialize(self, instance):
        if self.is_parental:
            return getattr(instance, self.name).all()
        return set()

    def populate_field(self, instance, value, context):
        pass


class RichTextAdapter(FieldAdapter):
    def get_object_references(self, instance):
        return get_reference_handler().get_objects(self.field.value_from_object(instance))

    def get_dependencies(self, value):
        return {
            (model, id, False)  # references in rich text are soft dependencies
            for model, id in get_reference_handler().get_objects(value)
        }

    def update_object_references(self, value, destination_ids_by_source):
        return get_reference_handler().update_ids(value, destination_ids_by_source)


class StreamFieldAdapter(FieldAdapter):
    def __init__(self, field):
        super().__init__(field)
        self.stream_block = self.field.stream_block

    def get_object_references(self, instance):
        # get the list of dicts representation of the streamfield json
        stream = self.stream_block.get_prep_value(self.field.value_from_object(instance))
        return get_object_references(self.stream_block, stream)

    def get_dependencies(self, value):
        return {
            (model, id, False)  # references in streamfield are soft dependencies
            for model, id in get_object_references(self.stream_block, json.loads(value))
        }

    def update_object_references(self, value, destination_ids_by_source):
        return json.dumps(update_object_ids(self.stream_block, json.loads(value), destination_ids_by_source))


class FileAdapter(FieldAdapter):
    def serialize(self, instance):
        value = self.field.value_from_object(instance)
        if not value:
            return None
        url = value.url
        if url.startswith('/'):
            # Using a relative media url. ie. /media/
            # Prepend the BASE_URL to turn this into an absolute URL
            if ADMIN_BASE_URL is None:
                raise ImproperlyConfigured(
                    "A WAGTAILADMIN_BASE_URL or BASE_URL setting must be provided when importing files"
                )
            url = ADMIN_BASE_URL.rstrip('/') + url
        return {
            'download_url': url,
            'size': get_file_size(self.field, instance),
            'hash': get_file_hash(self.field, instance),
        }

    def populate_field(self, instance, value, context):
        if not value:
            return None
        imported_file = context.imported_files_by_source_url.get(value['download_url'])
        if imported_file is None:

            existing_file = self.field.value_from_object(instance)

            if existing_file:
                existing_file_hash = get_file_hash(self.field, instance)
                if existing_file_hash == value['hash']:
                    # File not changed, so don't bother updating it
                    return

            # Get the local filename
            name = pathlib.PurePosixPath(urlparse(value['download_url']).path).name
            local_filename = self.field.generate_filename(instance, name)

            _file = File(local_filename, value['size'], value['hash'], value['download_url'])
            try:
                imported_file = _file.transfer()
            except FileTransferError:
                return None
            context.imported_files_by_source_url[_file.source_url] = imported_file

        value = imported_file.file.name
        getattr(instance, self.field.get_attname()).name = value


class ManyToManyFieldAdapter(FieldAdapter):
    def __init__(self, field):
        super().__init__(field)
        self.related_base_model = get_base_model(self.field.related_model)

    def _get_pks(self, instance):
        return [model.pk for model in self.field.value_from_object(instance)]

    def get_object_references(self, instance):
        refs = set()
        for pk in self._get_pks(instance):
            refs.add((self.related_base_model, pk))
        return refs

    def get_dependencies(self, value):
        return {(self.related_base_model, id, False) for id in value}

    def serialize(self, instance):
        pks = list(self._get_pks(instance))
        return pks

    def populate_field(self, instance, value, context):
        # setting forward ManyToMany directly is prohibited
        pass


class TaggableManagerAdapter(FieldAdapter):
    def populate_field(self, instance, value, context):
        # TODO
        pass


class GenericRelationAdapter(ManyToOneRelAdapter):
    pass


class AdapterRegistry:
    BASE_ADAPTERS_BY_FIELD_CLASS = {
        models.Field: FieldAdapter,
        models.ForeignKey: ForeignKeyAdapter,
        ManyToOneRel: ManyToOneRelAdapter,
        RichTextField: RichTextAdapter,
        StreamField: StreamFieldAdapter,
        models.FileField: FileAdapter,
        models.ManyToManyField: ManyToManyFieldAdapter,
        TaggableManager: TaggableManagerAdapter,
        GenericRelation: GenericRelationAdapter,
        GenericForeignKey: GenericForeignKeyAdapter,
    }

    def __init__(self):
        self._scanned_for_adapters = False
        self.adapters_by_field_class = {}

    def _scan_for_adapters(self):
        adapters = dict(self.BASE_ADAPTERS_BY_FIELD_CLASS)

        for fn in hooks.get_hooks('register_field_adapters'):
            adapters.update(fn())

        self.adapters_by_field_class = adapters
        self._scanned_for_adapters = True

    @lru_cache(maxsize=None)
    def get_field_adapter(self, field):
        # find the adapter class for the most specific class in the field's inheritance tree

        if not self._scanned_for_adapters:
            self._scan_for_adapters()

        for field_class in type(field).__mro__:
            if field_class in self.adapters_by_field_class:
                adapter_class = self.adapters_by_field_class[field_class]
                return adapter_class(field)


adapter_registry = AdapterRegistry()
