import uuid
import json

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.http import HttpResponse, JsonResponse, Http404
from django.urls import reverse
from django.views.decorators.http import require_POST
from django.shortcuts import get_object_or_404, render, redirect
import requests

from wagtail.core.models import Page

from .vendor.wagtail_admin_api.views import PagesAdminAPIViewSet
from .vendor.wagtail_api_v2.router import WagtailAPIRouter
from .models import IDMapping
from .serializers import get_model_serializer

from .operations import ImportPlanner


def pages_for_export(request, root_page_id):
    root_page = get_object_or_404(Page, id=root_page_id)

    pages = root_page.get_descendants(inclusive=True).specific()

    ids_for_import = [
        ['wagtailcore.page', page.pk] for page in pages
    ]

    objects = []
    object_references = set()

    for page in pages:
        serializer = get_model_serializer(type(page))
        objects.append(serializer.serialize(page))
        object_references.update(serializer.get_object_references(page))

    mappings = []
    for i, (model, pk) in enumerate(object_references):
        id_mapping, created = IDMapping.objects.get_or_create(
            content_type=ContentType.objects.get_for_model(model),
            local_id=pk,
            defaults={'uid': uuid.uuid1(clock_seq=i)}
        )
        mappings.append(
            [model._meta.label_lower, pk, id_mapping.uid]
        )

    return JsonResponse({
        'ids_for_import': ids_for_import,
        'mappings': mappings,
        'objects': objects,
    }, json_dumps_params={'indent': 2})


class PageChooserAPIViewSet(PagesAdminAPIViewSet):
    pass


def chooser_api_proxy(request, source_name, path):
    source_config = getattr(settings, 'WAGTAILTRANSFER_SOURCES', {}).get(source_name)

    if source_config is None:
        raise Http404("Source does not exist")

    base_url = source_config['BASE_URL'] + 'api/chooser/pages/'

    response = requests.get(f"{base_url}{path}?{request.GET.urlencode()}", headers={
        'Accept': request.META['HTTP_ACCEPT'],
    }, timeout=5)

    return HttpResponse(response.content, status=response.status_code)


def choose_page(request):
    return render(request, 'wagtail_transfer/choose_page.html', {
        'sources_data': json.dumps([
            {
                'value': source_name,
                'label': source_name,
                'page_chooser_api': reverse('wagtail_transfer_admin:chooser_api_proxy', args=[source_name, ''])
            }
            for source_name in getattr(settings, 'WAGTAILTRANSFER_SOURCES', {}).keys()
        ]),
    })


@require_POST
def do_import(request):
    source_config = settings.WAGTAILTRANSFER_SOURCES[request.POST['source']]
    response = requests.get(f"{source_config['BASE_URL']}api/pages/{request.POST['source_page_id']}/")

    importer = ImportPlanner(request.POST['source_page_id'], request.POST['dest_page_id'])
    importer.add_json(response.content)
    importer.run()

    return redirect('wagtailadmin_explore', request.POST['dest_page_id'])
