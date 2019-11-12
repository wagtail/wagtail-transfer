from django.conf.urls import url

from wagtail_transfer import views

urlpatterns = [
    url(r'^api/pages/(\d+)/$', views.pages_for_export, name='wagtail_transfer_pages'),
]
