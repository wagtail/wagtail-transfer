import uuid

from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist
from django.core.management.base import BaseCommand, ImproperlyConfigured

from wagtail_transfer.models import IDMapping, get_model_for_path, get_base_model


# Namespace UUID common to all wagtail-transfer installances, used with uuid5 to generate
# a predictable UUID for any given model-name / PK combination
NAMESPACE = uuid.UUID('418b5168-5a10-11ea-a84b-7831c1c42e66')


class Command(BaseCommand):
    help = "Pre-seed ID mappings used for content transfer"

    def add_arguments(self, parser):
        parser.add_argument('model_name', help="Model (as app_label.model_name) to populate table entries for, e.g. wagtailcore.Page")

    def handle(self, *args, **options):
        model_name = options['model_name'].lower()
        try:
            model = get_model_for_path(model_name)
        except ObjectDoesNotExist:
            raise ImproperlyConfigured("%r is not recognised as a model name." % model_name)

        if model != get_base_model(model):
            raise ImproperlyConfigured(
                "%r is not a valid model for ID mappings, as it is a subclass using multi-table inheritance." % model_name
            )

        content_type = ContentType.objects.get_for_model(model)
        # find IDs of instances of this model that already exist in the IDMapping table
        mapped_ids = IDMapping.objects.filter(content_type=content_type).values_list('local_id', flat=True)
        # these will be returned as strings, so convert to the pk field's native type
        mapped_ids = [model._meta.pk.to_python(id) for id in mapped_ids]

        # find IDs of instances not in this set
        unmapped_ids = model.objects.exclude(pk__in=mapped_ids).values_list('pk', flat=True)

        created_count = 0

        # create ID mapping for each of these
        for pk in unmapped_ids:
            _, created = IDMapping.objects.get_or_create(
                content_type=content_type, local_id=pk,
                defaults={'uid': uuid.uuid5(NAMESPACE, "%s:%s" % (model_name, pk))}
            )
            if created:
                created_count += 1

        if options['verbosity'] >= 1:
            print("%d ID mappings created." % created_count)
