from django.conf.urls import url

from wagtail_transfer import views

app_name = 'wagtail_transfer_admin'
urlpatterns = [
    url(r'^choose/$', views.choose_page, name='choose_page'),
    url(r'^api/chooser-proxy/(\w+)/([\w\-/]*)$', views.chooser_api_proxy, name='chooser_api_proxy'),
]
