from functools import lru_cache

from django.core.exceptions import ObjectDoesNotExist
from django.db import models
from django.db.models.constants import LOOKUP_SEP
from treebeard.mp_tree import MP_Node
from wagtail.core import hooks
from wagtail.core.models import Page

from .field_adapters import adapter_registry
from .models import get_base_model


def _get_subclasses_recurse(model):
    """
    Given a Model class, find all related objects, exploring children
    recursively, returning a `list` of strings representing the
    relations for select_related, adapted from https://github.com/jazzband/django-model-utils/blob/master/model_utils/managers.py
    """

    related_objects = [f for f in model._meta.get_fields() if isinstance(f, models.OneToOneRel)]

    rels = [
        rel for rel in related_objects
        if isinstance(rel.field, models.OneToOneField)
        and issubclass(rel.field.model, model)
        and model is not rel.field.model
        and rel.parent_link
    ]

    subclasses = []
    for rel in rels:
        for subclass in _get_subclasses_recurse(rel.field.model):
            subclasses.append(
                rel.get_accessor_name() + LOOKUP_SEP + subclass)
        subclasses.append(rel.get_accessor_name())
    return subclasses


def _get_sub_obj_recurse(obj, s):
    """
    Given an object and its potential subclasses in lookup string form,
    retrieve its most specific subclass recursively
    Taken from: https://github.com/jazzband/django-model-utils/blob/master/model_utils/managers.py
    """
    rel, _, s = s.partition(LOOKUP_SEP)

    try:
        node = getattr(obj, rel)
    except ObjectDoesNotExist:
        return None
    if s:
        child = _get_sub_obj_recurse(node, s)
        return child
    else:
        return node


def get_subclass_instances(instances, subclasses):
    subclass_instances = []
    for obj in instances:
        sub_obj = None
        for s in subclasses:
            sub_obj = _get_sub_obj_recurse(obj, s)
            if sub_obj:
                break
        if not sub_obj:
            sub_obj = obj
        subclass_instances.append(sub_obj)
    return subclass_instances


class ModelSerializer:
    ignored_fields = []

    def __init__(self, model):
        self.model = model
        self.base_model = get_base_model(model)

        field_adapters = []
        adapter_managed_fields = []
        for field in self.model._meta.get_fields():
            if field.name in self.ignored_fields:
                continue

            # ignore primary keys (including MTI parent pointers)
            if getattr(field, 'primary_key', False):
                continue

            adapter = adapter_registry.get_field_adapter(field)

            if adapter:
                adapter_managed_fields = adapter_managed_fields + adapter.get_managed_fields()
                field_adapters.append(adapter)

        self.field_adapters = [adapter for adapter in field_adapters if adapter.name not in adapter_managed_fields]

    def get_objects_by_ids(self, ids):
        """
        Given a list of IDs, return a list of model instances that we can
        run serialize and get_object_references on, fetching the specific subclasses
        if using multi table inheritance as appropriate
        """
        base_queryset = self.model.objects.filter(pk__in=ids)
        subclasses = _get_subclasses_recurse(self.model)
        return get_subclass_instances(base_queryset, subclasses)

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

    def get_objects_to_serialize(self, instance):
        objects = set()
        for f in self.field_adapters:
            objects.update(f.get_objects_to_serialize(instance))
        return objects


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
        return self.model.objects.filter(pk__in=ids).specific()


class SerializerRegistry:
    BASE_SERIALIZERS_BY_MODEL_CLASS = {
        models.Model: ModelSerializer,
        MP_Node: TreeModelSerializer,
        Page: PageSerializer,
    }

    def __init__(self):
        self._scanned_for_serializers = False
        self.serializers_by_model_class = {}

    def _scan_for_serializers(self):
        serializers = dict(self.BASE_SERIALIZERS_BY_MODEL_CLASS)

        for fn in hooks.get_hooks('register_custom_serializers'):
            serializers.update(fn())

        self.serializers_by_model_class = serializers
        self._scanned_for_serializers = True

    @lru_cache(maxsize=None)
    def get_model_serializer(self, model):
        # find the serializer class for the most specific class in the model's inheritance tree

        if not self._scanned_for_serializers:
            self._scan_for_serializers()

        for cls in model.__mro__:
            if cls in self.serializers_by_model_class:
                serializer_class = self.serializers_by_model_class[cls]
                return serializer_class(model)


serializer_registry = SerializerRegistry()
