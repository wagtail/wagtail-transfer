from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db import models


class IDMapping(models.Model):
    uid = models.UUIDField(primary_key=True)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    local_id = models.CharField(max_length=255)
    content_object = GenericForeignKey('content_type', 'local_id')

    class Meta:
        unique_together = ['content_type', 'local_id']
