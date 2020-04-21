from django.db import models

from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType


class IDMapping(models.Model):
    uid = models.UUIDField(primary_key=True)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    local_id = models.CharField(max_length=255)
    content_object = GenericForeignKey('content_type', 'local_id')

    class Meta:
        unique_together = ['content_type', 'local_id']


class ImportedFile(models.Model):
    file = models.FileField()
    source_url = models.URLField(max_length=1000)
    hash = models.CharField(max_length=40)
    size = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)


def get_base_model(model):
    """
    For the given model, return the highest concrete model in the inheritance tree -
    e.g. for BlogPage, return Page
    """
    if model._meta.parents:
        model = model._meta.get_parent_list()[0]
    return model


def get_model_for_path(model_path):
    """
    Given an 'app_name.model_name' string, return the model class
    """
    app_label, model_name = model_path.split('.')
    return ContentType.objects.get_by_natural_key(app_label, model_name).model_class()


def get_base_model_for_path(model_path):
    """
    Given an 'app_name.model_name' string, return the Model class for the base model
    (e.g. for 'blog.blog_page', return Page)
    """
    return get_base_model(get_model_for_path(model_path))
