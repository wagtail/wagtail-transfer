from collections import defaultdict
import json
from rest_framework import status
from rest_framework.fields import ReadOnlyField

from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.http import HttpResponse, JsonResponse, Http404
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.shortcuts import get_object_or_404, render, redirect
import requests

from wagtail.core.models import Page

from .auth import check_digest, digest_for_source
from .locators import get_locator_for_model
from .vendor.wagtail_admin_api.views import PagesAdminAPIViewSet
from .vendor.wagtail_admin_api.serializers import AdminPageSerializer
from .locators import get_locator_for_model

from .models import get_model_for_path
from .serializers import get_model_serializer

from .operations import ImportPlanner


def pages_for_export(request, root_page_id):
    check_digest(str(root_page_id), request.GET.get('digest', ''))

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
    for model, pk in object_references:
        uid = get_locator_for_model(model).get_uid_for_local_id(pk)
        mappings.append(
            [model._meta.label_lower, pk, uid]
        )

    return JsonResponse({
        'ids_for_import': ids_for_import,
        'mappings': mappings,
        'objects': objects,
    }, json_dumps_params={'indent': 2})


@csrf_exempt
@require_POST
def objects_for_export(request):
    """
    Accepts a POST request with a JSON payload structured as:
        {
            'model_label': [list of IDs],
            'model_label': [list of IDs],
        }
    and returns an API response with objects / mappings populated (but ids_for_import empty).
    """

    check_digest(request.body, request.GET.get('digest', ''))

    request_data = json.loads(request.body.decode('utf-8'))

    objects = []
    object_references = set()

    for model_path, ids in request_data.items():
        model = get_model_for_path(model_path)
        serializer = get_model_serializer(model)

        for obj in serializer.get_objects_by_ids(ids):
            instance_serializer = get_model_serializer(type(obj))
            objects.append(serializer.serialize(obj))
            object_references.update(serializer.get_object_references(obj))

    mappings = []
    for model, pk in object_references:
        uid = get_locator_for_model(model).get_uid_for_local_id(pk)
        mappings.append(
            [model._meta.label_lower, pk, uid]
        )

    return JsonResponse({
        'ids_for_import': [],
        'mappings': mappings,
        'objects': objects,
    }, json_dumps_params={'indent': 2})


class UIDField(ReadOnlyField):
    """
    Serializes UID for the Page Chooser API
    """
    def get_attribute(self, instance):
        return get_locator_for_model(Page).get_uid_for_local_id(instance.id, create=False)


class TransferPageChooserSerializer(AdminPageSerializer):
    uid = UIDField(read_only=True)


class PageChooserAPIViewSet(PagesAdminAPIViewSet):
    base_serializer_class = TransferPageChooserSerializer
    meta_fields = PagesAdminAPIViewSet.meta_fields + [
        'uid'
    ]
    listing_default_fields = PagesAdminAPIViewSet.listing_default_fields + [
        'uid'
    ]


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
    source = request.POST['source']
    base_url = settings.WAGTAILTRANSFER_SOURCES[source]['BASE_URL']
    digest = digest_for_source(source, str(request.POST['source_page_id']))

    response = requests.get(f"{base_url}api/pages/{request.POST['source_page_id']}/", params={'digest': digest})

    dest_page_id = request.POST['dest_page_id'] or None
    importer = ImportPlanner(request.POST['source_page_id'], dest_page_id)
    importer.add_json(response.content)

    while importer.missing_object_data:
        # convert missing_object_data from a set of (model_class, id) tuples
        # into a dict of {model_class_label: [list_of_ids]}
        missing_object_data_by_type = defaultdict(list)
        for model_class, source_id in importer.missing_object_data:
            missing_object_data_by_type[model_class].append(source_id)

        request_data = json.dumps({
            model_class._meta.label_lower: ids
            for model_class, ids in missing_object_data_by_type.items()
        })
        digest = digest_for_source(source, request_data)

        # request the missing object data and add to the import plan
        response = requests.post(
            f"{base_url}api/objects/", params={'digest': digest}, data=request_data
        )
        importer.add_json(response.content)

    importer.run()

    if dest_page_id:
        return redirect('wagtailadmin_explore', dest_page_id)
    else:
        return redirect('wagtailadmin_explore_root')


def check_page_existence_for_uid(request):
    """
    Check whether a page with the specified UID exists - used for checking whether a page has already been imported
    to the destination site
    """
    uid = request.GET.get('uid', '')
    locator = get_locator_for_model(Page)
    page_exists = bool(locator.find(uid))
    result = status.HTTP_200_OK if page_exists else status.HTTP_404_NOT_FOUND
    return HttpResponse('', status=result)
