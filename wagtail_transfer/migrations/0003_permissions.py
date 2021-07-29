from django.contrib.contenttypes.management import create_contenttypes
from django.db import migrations


def create_import_permission(apps, schema_editor):
    app_config = apps.get_app_config("wagtail_transfer")
    # Ensure content types from previous migrations are created. This is normally done
    # in a post_migrate signal, see
    # https://github.com/django/django/blob/3.2/django/contrib/contenttypes/apps.py#L21
    app_config.models_module = getattr(app_config, 'models_module', None) or True
    create_contenttypes(app_config)
    ContentType = apps.get_model("contenttypes", "ContentType")
    content_type = ContentType.objects.get(
        app_label="wagtail_transfer", model="idmapping"
    )
    Permission = apps.get_model("auth", "Permission")
    Permission.objects.get_or_create(
        content_type=content_type,
        codename="wagtailtransfer_can_import",
        name="Can import pages and snippets from other sites",
    )


def delete_import_permission(apps, schema_editor):
    ContentType = apps.get_model("contenttypes", "ContentType")
    content_type = ContentType.objects.get(
        app_label="wagtail_transfer", model="idmapping"
    )
    Permission = apps.get_model("auth", "Permission")
    permission = Permission.objects.filter(
        codename="wagtailtransfer_can_import",
        content_type=content_type,
    )
    permission.delete()


class Migration(migrations.Migration):

    dependencies = [
        ("auth", "0011_update_proxy_permissions"),
        ("contenttypes", "0002_remove_content_type_name"),
        ("wagtailcore", "0040_page_draft_title"),
        ("wagtail_transfer", "0002_importedfile"),
    ]

    operations = [
        migrations.RunPython(create_import_permission, delete_import_permission),
    ]
