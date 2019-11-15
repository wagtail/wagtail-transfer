from django.db import models
from django.db.models.fields.reverse_related import ManyToOneRel
from django.utils.encoding import is_protected_type

from .models import get_base_model


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


ADAPTERS_BY_FIELD_CLASS = {
    models.Field: FieldAdapter,
    models.ForeignKey: ForeignKeyAdapter,
    ManyToOneRel: ManyToOneRelAdapter,
}


def get_field_adapter(field):
    # find the adapter class for the most specific class in the field's inheritance tree
    for field_class in type(field).__mro__:
        if field_class in ADAPTERS_BY_FIELD_CLASS:
            adapter_class = ADAPTERS_BY_FIELD_CLASS[field_class]
            return adapter_class(field)

    raise ValueError("No adapter found for field: %r" % field)
