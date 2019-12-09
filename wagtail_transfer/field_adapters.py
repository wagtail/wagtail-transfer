from django.db import models
from django.db.models.fields.reverse_related import ManyToOneRel
from django.utils.encoding import is_protected_type

from modelcluster.fields import ParentalManyToManyField

from wagtail.core.fields import RichTextField, StreamField

from .files import get_file_size, get_file_hash
from .models import get_base_model
from .richtext import get_reference_handler
from .streamfield import get_object_references


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


class RichTextAdapter(FieldAdapter):
    def get_object_references(self, instance):
        return get_reference_handler().get_objects(self.field.value_from_object(instance))


class StreamFieldAdapter(FieldAdapter):
    def get_object_references(self, instance):
        stream_block = self.field.stream_block

        #get the list of dicts representation of the streamfield json
        stream = stream_block.get_prep_value(self.field.value_from_object(instance))
        return get_object_references(stream_block, stream)


class FileAdapter(FieldAdapter):
    def serialize(self, instance):
        return {
            'download_url': self.field.value_from_object(instance).url,
            'size': get_file_size(self.field, instance),
            'hash': get_file_hash(self.field, instance),
        }


class ParentalManyToManyFieldAdapter(FieldAdapter):
    def __init__(self, field):
        super().__init__(field)
        self.related_base_model = get_base_model(self.field.related_model)

    def _get_pks(self, instance):
        return self.field.value_from_object(instance).values_list('pk', flat=True)

    def get_object_references(self, instance):
        refs = set()
        for pk in self._get_pks(instance):
            refs.add((self.related_base_model, pk))
        return refs

    def serialize(self, instance):
        pks = list(self._get_pks(instance))
        return pks


ADAPTERS_BY_FIELD_CLASS = {
    models.Field: FieldAdapter,
    models.ForeignKey: ForeignKeyAdapter,
    ManyToOneRel: ManyToOneRelAdapter,
    RichTextField: RichTextAdapter,
    StreamField: StreamFieldAdapter,
    models.FileField: FileAdapter,
    ParentalManyToManyField: ParentalManyToManyFieldAdapter,
}


def get_field_adapter(field):
    # find the adapter class for the most specific class in the field's inheritance tree
    for field_class in type(field).__mro__:
        if field_class in ADAPTERS_BY_FIELD_CLASS:
            adapter_class = ADAPTERS_BY_FIELD_CLASS[field_class]
            return adapter_class(field)

    raise ValueError("No adapter found for field: %r" % field)
