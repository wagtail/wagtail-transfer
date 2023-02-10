import uuid

from django.apps import apps
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist
from django.core.management.base import BaseCommand, CommandError

from wagtail_transfer.models import (IDMapping, get_base_model,
                                     get_model_for_path)

# Namespace UUID common to all wagtail-transfer installances, used with uuid5 to generate
# a predictable UUID for any given model-name / PK combination
NAMESPACE = uuid.UUID('418b5168-5a10-11ea-a84b-7831c1c42e66')


class Command(BaseCommand):
    help = "Pre-seed ID mappings used for content transfer"

    def add_arguments(self, parser):
        parser.add_argument('labels', metavar='model_or_app', nargs='+', help="Model (as app_label.model_name) or app name to populate table entries for, e.g. wagtailcore.Page or wagtailcore")
        parser.add_argument('--range', help="Range of IDs to create mappings for (e.g. 1-1000)")

    def handle(self, *args, **options):
        models = []
        for label in options['labels']:
            label = label.lower()
            if '.' in label:
                # interpret as a model
                try:
                    model = get_model_for_path(label)
                except ObjectDoesNotExist:
                    raise CommandError("%r is not recognised as a model name." % label)

                if model != get_base_model(model):
                    raise CommandError(
                        "%r is not a valid model for ID mappings, as it is a subclass using multi-table inheritance." % label
                    )

                models.append(model)
            else:
                # interpret label as an app
                try:
                    app = apps.get_app_config(label)
                except LookupError:
                    raise CommandError("%r is not recognised as an app label." % label)

                for model in app.get_models():
                    if model == get_base_model(model):
                        models.append(model)

        created_count = 0

        for model in models:
            model_name = "%s.%s" % (model._meta.app_label, model._meta.model_name)

            content_type = ContentType.objects.get_for_model(model)
            # find IDs of instances of this model that already exist in the IDMapping table
            mapped_ids = IDMapping.objects.filter(content_type=content_type).values_list('local_id', flat=True)

            # these will be returned as strings, so convert to the pk field's native type
            mapped_ids = [model._meta.pk.to_python(id) for id in mapped_ids]

            # find IDs of instances not in this set
            unmapped_ids = model.objects.exclude(pk__in=mapped_ids).values_list('pk', flat=True)

            # apply ID range filter if passed
            if options['range']:
                min_id, max_id = options['range'].split('-')
                unmapped_ids = unmapped_ids.filter(pk__gte=min_id, pk__lte=max_id)

            # create ID mapping for each of these
            for pk in unmapped_ids:
                _, created = IDMapping.objects.get_or_create(
                    content_type=content_type, local_id=pk,
                    defaults={'uid': uuid.uuid5(NAMESPACE, "%s:%s" % (model_name, pk))}
                )
                if created:
                    created_count += 1

        if options['verbosity'] >= 1:
            self.stdout.write("%d ID mappings created." % created_count)
