# Generated by Django 2.2.6 on 2019-12-12 17:37

import modelcluster.fields
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tests', '0008_author'),
    ]

    operations = [
        migrations.CreateModel(
            name='Category',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255, unique=True)),
                ('colour', models.CharField(blank=True, max_length=255, null=True)),
            ],
        ),
        migrations.AddField(
            model_name='sponsoredpage',
            name='categories',
            field=modelcluster.fields.ParentalManyToManyField(to='tests.Category'),
        ),
    ]
