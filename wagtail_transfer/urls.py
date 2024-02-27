from django.urls import path, re_path
from wagtail.utils.urlpatterns import decorate_urlpatterns

from wagtail_transfer import views
from wagtail_transfer.auth import check_get_digest_wrapper
from wagtail_transfer.vendor.wagtail_api_v2.views import ModelsAPIViewSet

from .vendor.wagtail_api_v2.router import WagtailAPIRouter

chooser_api = WagtailAPIRouter('wagtail_transfer_page_chooser_api')
chooser_api.register_endpoint('pages', views.PageChooserAPIViewSet)
chooser_api.register_endpoint('models', ModelsAPIViewSet)

urlpatterns = [
    re_path(r'^api/pages/(\d+)/$', views.pages_for_export, name='wagtail_transfer_pages'),
    path('api/models/<str:model_path>/', views.models_for_export, name='wagtail_transfer_model'),
    path('api/models/<str:model_path>/<int:object_id>/', views.models_for_export, name='wagtail_transfer_model_object'),
    path('api/objects/', views.objects_for_export, name='wagtail_transfer_objects'),
    re_path(r'^api/chooser/', (decorate_urlpatterns(chooser_api.get_urlpatterns(), check_get_digest_wrapper), chooser_api.url_namespace, chooser_api.url_namespace)),
]
