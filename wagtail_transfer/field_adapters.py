import json
import pathlib
from functools import lru_cache
from urllib.parse import urlparse

from django.conf import settings
from django.db import models
from django.db.models.fields.reverse_related import ManyToOneRel
from taggit.managers import TaggableManager
from wagtail.core.fields import RichTextField, StreamField

from .files import File, FileTransferError, get_file_hash, get_file_size
from .models import get_base_model
from .richtext import get_reference_handler
from .streamfield import get_object_references, update_object_ids

from django.contrib.contenttypes.fields import GenericRelation

from django.utils.encoding import is_protected_type


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
        setattr(instance, self.field.get_attname(), value)


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


class ManyToOneRelAdapter(FieldAdapter):
    def __init__(self, field):
        super().__init__(field)
        self.related_field = field.field
        self.related_model = field.related_model

        from .serializers import get_model_serializer
        self.related_model_serializer = get_model_serializer(self.related_model)

    def _get_related_objects(self, instance):
        return getattr(instance, self.name).all()

    def serialize(self, instance):
        return [
            self.related_model_serializer.serialize(obj)
            for obj in self._get_related_objects(instance)
        ]

    def get_object_references(self, instance):
        refs = set()
        for obj in self._get_related_objects(instance):
            refs.update(self.related_model_serializer.get_object_references(obj))
        return refs

    def populate_field(self, instance, value, context):
        raise Exception('populate_field is not supported on many-to-one relations')


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
            (model, id, False)  # references in rich text are soft dependencies
            for model, id in get_object_references(self.stream_block, json.loads(value))
        }

    def update_object_references(self, value, destination_ids_by_source):
        return json.dumps(update_object_ids(self.stream_block, json.loads(value), destination_ids_by_source))


class FileAdapter(FieldAdapter):
    def serialize(self, instance):
        url = self.field.value_from_object(instance).url
        if settings.MEDIA_URL.startswith('/'):
            # Using a relative media url. ie. /media/
            # Prepend the BASE_URL to turn this into an absolute URL
            url = settings.BASE_URL.rstrip('/') + url
        return {
            'download_url': url,
            'size': get_file_size(self.field, instance),
            'hash': get_file_hash(self.field, instance),
        }

    def populate_field(self, instance, value, context):
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


class GenericRelationAdapter(FieldAdapter):
    def populate_field(self, instance, value, context):
        # TODO
        pass


ADAPTERS_BY_FIELD_CLASS = {
    models.Field: FieldAdapter,
    models.ForeignKey: ForeignKeyAdapter,
    ManyToOneRel: ManyToOneRelAdapter,
    RichTextField: RichTextAdapter,
    StreamField: StreamFieldAdapter,
    models.FileField: FileAdapter,
    models.ManyToManyField: ManyToManyFieldAdapter,
    TaggableManager: TaggableManagerAdapter,
    GenericRelation: GenericRelationAdapter,
}


@lru_cache(maxsize=None)
def get_field_adapter(field):
    # find the adapter class for the most specific class in the field's inheritance tree

    for field_class in type(field).__mro__:
        if field_class in ADAPTERS_BY_FIELD_CLASS:
            adapter_class = ADAPTERS_BY_FIELD_CLASS[field_class]
            return adapter_class(field)

    raise ValueError("No adapter found for field: %r" % field)
