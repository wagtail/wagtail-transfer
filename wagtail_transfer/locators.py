"""
Helper objects for locating a database object according to some lookup criterion understood across
all sites - usually a UUID to look up in the IDMapping table, but may be something else
model-specific such as a slug field.
"""
import logging
import uuid
from functools import lru_cache

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ImproperlyConfigured
from django.db import IntegrityError

from .models import IDMapping, get_base_model


logger = logging.getLogger(__name__)

UUID_SEQUENCE = 0

# dict of models that should be located by field values using FieldLocator,
# rather than by UUID mapping
LOOKUP_FIELDS = {
    'taggit.tag': ['slug'],  # sensible default for taggit; can still be overridden 
    'wagtailcore.locale': ["language_code"],
    'contenttypes.contenttype': ['app_label', 'model'],
}
for model_label, fields in getattr(settings, 'WAGTAILTRANSFER_LOOKUP_FIELDS', {}).items():
    LOOKUP_FIELDS[model_label.lower()] = fields


class IDMappingLocator:
    def __init__(self, model):
        if model._meta.parents:
            raise ImproperlyConfigured(
                "IDMappingLocator cannot be used on MTI subclasses (got %r)" % model
            )
        self.model = model
        self.content_type = ContentType.objects.get_for_model(model)

    def find(self, uid):
        """Find object by UID; return None if not found"""

        try:
            mapping = IDMapping.objects.get(uid=uid)
        except IDMapping.DoesNotExist:
            logger.debug(f"IDMapping not found for {uid}")
            return None

        if mapping.content_type != self.content_type:
            raise IntegrityError(
                "Content type mismatch! Expected %r, got %r" % (self.content_type, mapping.content_type)
            )

        return mapping.content_object

    def get_uid_for_local_id(self, id, create=True):
        global UUID_SEQUENCE

        if create:
            """Get UID for the instance with the given ID (assigning one if one doesn't exist already)"""
            id_mapping, created = IDMapping.objects.get_or_create(
                content_type=self.content_type,
                local_id=id,
                defaults={'uid': uuid.uuid1(clock_seq=UUID_SEQUENCE)}
            )
            UUID_SEQUENCE += 1

            return id_mapping.uid
        else:
            """Get UID for the instance with the given ID (returning None if one doesn't exist)"""
            try:
                id_mapping = IDMapping.objects.get(
                    content_type=self.content_type,
                    local_id=id
                )
                return id_mapping.uid
            except IDMapping.DoesNotExist:
                logger.debug(f"IDMapping for local_id not found for {id}")
                return None

    def attach_uid(self, instance, uid):
        """
        Do whatever needs to be done to ensure that the given instance can be located under the
        given UID in future runs
        """
        if not isinstance(instance, self.model):
            raise IntegrityError(
                "IDMappingLocator expected a %s instance, got %r" % (self.model, instance)
            )

        # use update_or_create to account for the possibility of an existing IDMapping for the same
        # UID, left over from the object being previously imported and then deleted
        IDMapping.objects.update_or_create(
            uid=uid, defaults={'content_type': self.content_type, 'local_id': instance.pk}
        )

    def uid_from_json(self, json_uid):
        """
        Convert the UID representation originating from JSON data into the native type used by
        this locator
        """
        # No conversion necessary, as UID is a string, and JSON handles those fine...
        return json_uid


class FieldLocator:
    def __init__(self, model, fields):
        if model._meta.parents:
            raise ImproperlyConfigured(
                "FieldLocator cannot be used on MTI subclasses (got %r)" % model
            )
        self.model = model
        self.fields = fields

    def get_uid_for_local_id(self, id, **kwargs):
        # For field-based lookups, the UID is a tuple of field values
        return self.model.objects.values_list(*self.fields).get(pk=id)

    def attach_uid(self, instance, uid):
        # UID is derived directly from the object data, so nothing needs to be done to associate
        # the UID with the object
        pass

    def uid_from_json(self, json_uid):
        # A UID coming from JSON data will arrive as a list (because JSON has no tuple type),
        # but we need a tuple because the importer logic expects a hashable type that we can use
        # in sets and dict keys
        return tuple(json_uid)

    def find(self, uid):
        # pair up field names with their respective items in the UID tuple, to form a filter dict
        # that we can use for an ORM lookup
        filters = dict(zip(self.fields, uid))

        try:
            return self.model.objects.get(**filters)
        except self.model.DoesNotExist:
            logger.debug(f"Couldn't find {self.model} using {filters}, returning None")
            return None


@lru_cache(maxsize=None)
def get_locator_for_model(model):
    base_model = get_base_model(model)
    try:
        # Use FieldLocator if an entry exists in LOOKUP_FIELDS
        fields = LOOKUP_FIELDS[base_model._meta.label_lower]
        return FieldLocator(base_model, fields)
    except KeyError as e:
        logger.debug(f"{base_model} FieldLocator lookup for {e} failed. Falling back to IDMappingLocator")
        return IDMappingLocator(base_model)
