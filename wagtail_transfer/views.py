import json
from collections import defaultdict

import requests
from django.conf import settings
from django.contrib.auth.decorators import permission_required
from django.http import Http404, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from rest_framework import status
from rest_framework.fields import ReadOnlyField
from wagtail.core.models import Page

from .auth import check_digest, digest_for_source
from .locators import get_locator_for_model
from .models import get_model_for_path
from .operations import ImportPlanner
from .serializers import serializer_registry
from .vendor.wagtail_admin_api.serializers import AdminPageSerializer
from .vendor.wagtail_admin_api.views import PagesAdminAPIViewSet

from django.contrib import messages
from django.contrib.contenttypes.models import ContentType


def pages_for_export(request, root_page_id):
    check_digest(str(root_page_id), request.GET.get('digest', ''))

    root_page = get_object_or_404(Page, id=root_page_id)

    pages = [root_page.specific] if request.GET.get('recursive', 'true') == 'false' else root_page.get_descendants(inclusive=True).specific()

    ids_for_import = [
        ['wagtailcore.page', page.pk] for page in pages
    ]

    objects = []
    object_references = set()

    models_to_serialize = set(pages)
    serialized_models = set()

    while models_to_serialize:
        model = models_to_serialize.pop()
        serializer = serializer_registry.get_model_serializer(type(model))
        objects.append(serializer.serialize(model))
        object_references.update(serializer.get_object_references(model))
        models_to_serialize.update(serializer.get_objects_to_serialize(model).difference(serialized_models))

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


def models_for_export(request, model_path, object_id=None):
    """
    Return data for a specific model based on the incoming model_path.

    If an object_id is provided, search for a single model object.
    """
    check_digest(str(model_path), request.GET.get('digest', ''))

    # 1. Confirm whether or not th model_path leads to a real model.
    app_label, model_name = model_path.split('.')
    Model = ContentType.objects.get_by_natural_key(app_label, model_name).model_class()

    if object_id is None:
        model_objects = Model.objects.all()
    else:
        model_objects = [Model.objects.get(pk=object_id)]

    # 2. If this was just a model and not a specific object, get all child IDs.
    ids_for_import = [
        [model_path, obj.pk] for obj in model_objects
    ]

    objects = []
    object_references = set()

    models_to_serialize = set(model_objects)
    serialized_models = set()

    while models_to_serialize:
        model = models_to_serialize.pop()
        serializer = serializer_registry.get_model_serializer(type(model))
        objects.append(serializer.serialize(model))
        object_references.update(serializer.get_object_references(model))
        models_to_serialize.update(serializer.get_objects_to_serialize(model).difference(serialized_models))

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
    serialized_models = set()
    models_to_serialize = set()

    for model_path, ids in request_data.items():
        model = get_model_for_path(model_path)
        serializer = serializer_registry.get_model_serializer(model)

        models_to_serialize.update(serializer.get_objects_by_ids(ids))
        while models_to_serialize:
            instance = models_to_serialize.pop()
            serializer = serializer_registry.get_model_serializer(type(instance))
            objects.append(serializer.serialize(instance))
            object_references.update(serializer.get_object_references(instance))
            models_to_serialize.update(serializer.get_objects_to_serialize(instance).difference(serialized_models))

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


@permission_required(
    "wagtail_transfer.wagtailtransfer_can_import", login_url="wagtailadmin_login"
)
def chooser_api_proxy(request, source_name, path):
    source_config = getattr(settings, 'WAGTAILTRANSFER_SOURCES', {}).get(source_name)

    api_proxy_timeout_seconds = getattr(settings, 'WAGTAILTRANSFER_CHOOSER_API_PROXY_TIMEOUT', 5)

    if source_config is None:
        raise Http404("Source does not exist")

    default_chooser_endpoint = 'pages'
    if 'models' in request.GET:
        default_chooser_endpoint = 'models'

    base_url = source_config['BASE_URL'] + 'api/chooser/{}/'.format(default_chooser_endpoint)

    response = requests.get(f"{base_url}{path}?{request.GET.urlencode()}", headers={
        'Accept': request.META['HTTP_ACCEPT'],
    }, timeout=api_proxy_timeout_seconds)

    return HttpResponse(response.content, status=response.status_code)


@permission_required(
    "wagtail_transfer.wagtailtransfer_can_import", login_url="wagtailadmin_login"
)
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


def import_missing_object_data(source, importer: ImportPlanner):
    base_url = settings.WAGTAILTRANSFER_SOURCES[source]['BASE_URL']
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
    return importer


def import_page(request):
    source = request.POST['source']
    base_url = settings.WAGTAILTRANSFER_SOURCES[source]['BASE_URL']
    digest = digest_for_source(source, str(request.POST['source_page_id']))

    response = requests.get(f"{base_url}api/pages/{request.POST['source_page_id']}/", params={'digest': digest})

    dest_page_id = request.POST['dest_page_id'] or None
    importer = ImportPlanner.for_page(source=request.POST['source_page_id'], destination=dest_page_id)
    importer.add_json(response.content)
    importer = import_missing_object_data(source, importer)

    if dest_page_id:
        return redirect('wagtailadmin_explore', dest_page_id)
    else:
        return redirect('wagtailadmin_explore_root')


def import_model(request):
    source = request.POST['source']
    model = request.POST['source_model']
    base_url = settings.WAGTAILTRANSFER_SOURCES[source]['BASE_URL']
    digest = digest_for_source(source, model)

    url = f"{base_url}api/models/{model}/"
    if request.POST.get("source_model_object_id"):
        source_model_object_id = request.POST.get("source_model_object_id")
        url = f"{url}{source_model_object_id}/"

    response = requests.get(url, params={'digest': digest})
    importer = ImportPlanner.for_model(model=model)
    importer.add_json(response.content)
    importer = import_missing_object_data(source, importer)

    messages.add_message(request, messages.SUCCESS, 'Snippet(s) successfully imported')
    app_label, model_name = model.split('.')
    return redirect('wagtailsnippets:list', app_label, model_name)


@permission_required(
    "wagtail_transfer.wagtailtransfer_can_import", login_url="wagtailadmin_login"
)
@require_POST
def do_import(request):
    post_type = request.POST.get('type', 'page')
    if post_type == 'page':
        return import_page(request)
    elif post_type == 'model':
        return import_model(request)


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
