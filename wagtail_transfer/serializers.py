from functools import lru_cache

from django.db import models
from wagtail.core.models import Page

from .field_adapters import get_field_adapter


class ModelSerializer:
    ignored_fields = []

    def __init__(self, model):
        self.model = model

        self.field_adapters = []
        for field in self.model._meta.get_fields():
            try:
                # ignore primary keys (including MTI parent pointers)
                if field.primary_key:
                    continue
            except AttributeError:
                # ignore 'fake' fields such as reverse relations, that don't have
                # standard attributes such as primary_key
                continue

            if field.name in self.ignored_fields:
                continue

            self.field_adapters.append(get_field_adapter(field))

    def serialize_fields(self, instance):
        return {
            field_adapter.name: field_adapter.serialize(instance)
            for field_adapter in self.field_adapters
        }

    def serialize(self, instance):
        return {
            'model': self.model._meta.label_lower,
            'pk': instance.pk,
            'fields': self.serialize_fields(instance)
        }

    def get_object_references(self, instance):
        refs = set()
        for f in self.field_adapters:
            refs.update(f.get_object_references(instance))
        return refs


class PageSerializer(ModelSerializer):
    ignored_fields = [
        'path', 'depth', 'numchild', 'url_path', 'content_type', 'draft_title', 'has_unpublished_changes', 'owner',
        'go_live_at', 'expire_at', 'expired', 'locked', 'first_published_at', 'last_published_at',
        'latest_revision_created_at', 'live_revision',
    ]

    def serialize(self, instance):
        result = super().serialize(instance)
        if instance.is_root():
            result['parent_id'] = None
        else:
            result['parent_id'] = instance.get_parent().pk
        return result


SERIALIZERS_BY_MODEL_CLASS = {
    models.Model: ModelSerializer,
    Page: PageSerializer,
}


@lru_cache(maxsize=None)
def get_model_serializer(model):
    # find the serializer class for the most specific class in the model's inheritance tree
    for cls in model.__mro__:
        if cls in SERIALIZERS_BY_MODEL_CLASS:
            serializer_class = SERIALIZERS_BY_MODEL_CLASS[cls]
            return serializer_class(model)
