from __future__ import absolute_import, unicode_literals

from django.urls import include, path
from wagtail import urls as wagtail_urls
from wagtail.admin import urls as wagtailadmin_urls

from wagtail_transfer import urls as wagtailtransfer_urls

urlpatterns = [
    path('admin/', include(wagtailadmin_urls)),
    path('wagtail-transfer/', include(wagtailtransfer_urls)),

    # For anything not caught by a more specific rule above, hand over to
    # Wagtail's serving mechanism
    path('', include(wagtail_urls)),
]
