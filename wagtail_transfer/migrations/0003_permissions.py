from django.db import migrations


def create_import_permission(apps, schema_editor):
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
        codename="wagtailtransfer_can_import", content_type=content_type,
    )
    permission.delete()


class Migration(migrations.Migration):

    dependencies = [
        ("auth", "0011_update_proxy_permissions"),
        ("contenttypes", "0002_remove_content_type_name"),
        ("wagtailcore", "0060_fix_workflow_unique_constraint"),
        ("wagtail_transfer", "0002_importedfile"),
    ]

    operations = [
        migrations.RunPython(create_import_permission, delete_import_permission),
    ]
