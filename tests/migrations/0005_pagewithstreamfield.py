# Generated by Django 2.2.7 on 2019-12-04 17:28

import django.db.models.deletion
import wagtail.blocks
import wagtail.fields
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('wagtailcore', '0041_group_collection_permissions_verbose_name_plural'),
        ('tests', '0004_pagewithrichtext'),
    ]

    operations = [
        migrations.CreateModel(
            name='PageWithStreamField',
            fields=[
                ('page_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='wagtailcore.Page')),
                ('body', wagtail.fields.StreamField([('link_block', wagtail.blocks.StructBlock([('page', wagtail.blocks.PageChooserBlock()), ('text', wagtail.blocks.CharBlock(max_length=250))])), ('page', wagtail.blocks.PageChooserBlock()), ('stream', wagtail.blocks.StreamBlock([('page', wagtail.blocks.PageChooserBlock())])), ('rich_text', wagtail.blocks.RichTextBlock()), ('list_of_pages', wagtail.blocks.ListBlock(wagtail.blocks.PageChooserBlock()))], blank=True, verbose_name='Page body')),
            ],
            options={
                'abstract': False,
            },
            bases=('wagtailcore.page',),
        ),
    ]
