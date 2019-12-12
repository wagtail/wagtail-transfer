"""
Helper objects for locating a database object according to some lookup criterion understood across
all sites - usually a UUID to look up in the IDMapping table, but may be something else
model-specific such as a slug field.
"""

from functools import lru_cache
import uuid

from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ImproperlyConfigured
from django.db import IntegrityError

from .models import IDMapping, get_base_model


UUID_SEQUENCE = 0


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
            return None

        if mapping.content_type != self.content_type:
            raise IntegrityError(
                "Content type mismatch! Expected %r, got %r" % (self.content_type, mapping.content_type)
            )

        return mapping.content_object

    def get_uid_for_local_id(self, id):
        global UUID_SEQUENCE

        """Get UID for the instance with the given ID (assigning one if one doesn't exist already)"""
        id_mapping, created = IDMapping.objects.get_or_create(
            content_type=self.content_type,
            local_id=id,
            defaults={'uid': uuid.uuid1(clock_seq=UUID_SEQUENCE)}
        )
        UUID_SEQUENCE += 1

        return id_mapping.uid

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


@lru_cache(maxsize=None)
def get_locator_for_model(model):
    return IDMappingLocator(get_base_model(model))
