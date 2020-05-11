from functools import lru_cache

from django.db import models
from modelcluster.fields import ParentalKey
from treebeard.mp_tree import MP_Node
from wagtail.core.models import Page

from .field_adapters import get_field_adapter
from .models import get_base_model


class ModelSerializer:
    ignored_fields = []

    def __init__(self, model):
        self.model = model
        self.base_model = get_base_model(model)

        self.field_adapters = []
        for field in self.model._meta.get_fields():
            if field.name in self.ignored_fields:
                continue

            if isinstance(field, models.Field):
                # this is a genuine field rather than a reverse relation

                # ignore primary keys (including MTI parent pointers)
                if field.primary_key:
                    continue
            else:
                # this is probably a reverse relation, so fetch its related field
                try:
                    related_field = field.field
                except AttributeError:
                    # we don't know what sort of pseudo-field this is, so skip it
                    continue

                # ignore relations other than ParentalKey
                if not isinstance(related_field, ParentalKey):
                    continue

            self.field_adapters.append(get_field_adapter(field))

    def get_objects_by_ids(self, ids):
        """
        Given a list of IDs, return a queryset of model instances that we can
        run serialize and get_object_references on
        """
        return self.model.objects.filter(pk__in=ids)

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
        refs = {
            # always include the primary key as an object reference
            (self.base_model, instance.pk)
        }
        for f in self.field_adapters:
            refs.update(f.get_object_references(instance))
        return refs


class TreeModelSerializer(ModelSerializer):
    ignored_fields = ['path', 'depth', 'numchild']

    def serialize(self, instance):
        result = super().serialize(instance)
        if instance.is_root():
            result['parent_id'] = None
        else:
            result['parent_id'] = instance.get_parent().pk

        return result

    def get_object_references(self, instance):
        refs = super().get_object_references(instance)
        if not instance.is_root():
            # add a reference for the parent ID
            refs.add(
                (self.base_model, instance.get_parent().pk)
            )
        return refs


class PageSerializer(TreeModelSerializer):
    ignored_fields = TreeModelSerializer.ignored_fields + [
        'url_path', 'content_type', 'draft_title', 'has_unpublished_changes', 'owner',
        'go_live_at', 'expire_at', 'expired', 'locked', 'first_published_at', 'last_published_at',
        'latest_revision_created_at', 'live_revision',
    ]

    def get_objects_by_ids(self, ids):
        # serialize method needs the instance in its specific form
        return super().get_objects_by_ids(ids).specific()


SERIALIZERS_BY_MODEL_CLASS = {
    models.Model: ModelSerializer,
    MP_Node: TreeModelSerializer,
    Page: PageSerializer,
}


@lru_cache(maxsize=None)
def get_model_serializer(model):
    # find the serializer class for the most specific class in the model's inheritance tree
    for cls in model.__mro__:
        if cls in SERIALIZERS_BY_MODEL_CLASS:
            serializer_class = SERIALIZERS_BY_MODEL_CLASS[cls]
            return serializer_class(model)
