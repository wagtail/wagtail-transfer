from django.urls import include, re_path
from wagtail import urls as wagtail_urls
from wagtail.admin import urls as wagtailadmin_urls

from wagtail_transfer import urls as wagtailtransfer_urls

urlpatterns = [
    re_path(r"^admin/", include(wagtailadmin_urls)),
    re_path(r"^wagtail-transfer/", include(wagtailtransfer_urls)),
    # For anything not caught by a more specific rule above, hand over to
    # Wagtail's serving mechanism
    re_path(r"", include(wagtail_urls)),
]
