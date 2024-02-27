from django.urls import path, re_path

from wagtail_transfer import views

from .vendor.wagtail_api_v2.router import WagtailAPIRouter

chooser_api = WagtailAPIRouter('wagtail_transfer_admin:page_chooser_api')
chooser_api.register_endpoint('pages', views.PageChooserAPIViewSet)

app_name = 'wagtail_transfer_admin'
urlpatterns = [
    path('choose/', views.choose_page, name='choose_page'),
    path('import/', views.do_import, name='import'),
    re_path(r'^api/chooser-local/', (chooser_api.urls[0], 'page_chooser_api', 'page_chooser_api')),
    re_path(r'^api/chooser-proxy/(\w+)/([\w\-/]*)$', views.chooser_api_proxy, name='chooser_api_proxy'),
    path('api/check_uid/', views.check_page_existence_for_uid, name='check_uid'),
]
