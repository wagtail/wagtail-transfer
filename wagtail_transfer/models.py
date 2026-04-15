from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ImproperlyConfigured
from django.db import models


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

def get_model_transformation_config():
    """
    Get the model transformation configuration from the settings, or return an empty dict

    The model transformation configuration is a dictionary that defines which target model
    should receive data from a source model during import.

    Example: {'app_name.model_name': 'another_app_name.another_model_name'}
    """
    return getattr(settings, "WAGTAILTRANSFER_MODEL_TRANSFORMATION", {})


def transform_model(model_path):
    """
    Transform a source model path to a target model path using the model transformation
    configuration.

    If the model path is not in the transformation configuration, return the original model path.
    Keys are normalized for case-insensitive matching.
    (e.g. for 'source_app.source_model', return 'target_app.target_model')
    """
    model_transformation = get_model_transformation_config()
    normalized_transformation = {
        normalize_model_label(k): v for k, v in model_transformation.items()
    }
    return normalized_transformation.get(normalize_model_label(model_path), model_path)


def reverse_transform_model(model_path):
    """
    Reverse-transform a destination model path back to its source model path using the model
    transformation configuration.

    If the model path is not a value in the transformation configuration, return the original
    model path (i.e. no reverse transformation is needed).

    This is used when the destination site needs to request missing object data from the
    source site using the source's model labels.
    """
    model_transformation = get_model_transformation_config()
    normalized_path = normalize_model_label(model_path)
    reverse_transformation = {}
    for source_label, dest_label in model_transformation.items():
        normalized_dest = normalize_model_label(dest_label)
        if normalized_dest in reverse_transformation:
            raise ImproperlyConfigured(
                f"WAGTAILTRANSFER_MODEL_TRANSFORMATION has multiple source models transforming to "
                f"'{dest_label}': '{reverse_transformation[normalized_dest]}' and '{source_label}'. "
                f"Many-to-one model transformation is not supported."
            )
        reverse_transformation[normalized_dest] = source_label
    return reverse_transformation.get(normalized_path, model_path)


def get_model_for_path(model_path):
    """
    Given an 'app_name.model_name' string, return the model class

    This function also supports transforming the model to another model using the model transformation configuration
    """
    model_path = transform_model(model_path)
    app_label, model_name = model_path.split('.')
    return ContentType.objects.get_by_natural_key(app_label, model_name).model_class()


def get_base_model_for_path(model_path):
    """
    Given an 'app_name.model_name' string, return the Model class for the base model
    (e.g. for 'blog.blog_page', return Page)
    """
    return get_base_model(get_model_for_path(model_path))


def normalize_model_label(label):
    app_label, model_name = label.rsplit('.', 1)
    return "{}.{}".format(app_label, model_name.lower())
    