from django.conf import settings
from django.conf.urls import include, url
from django.urls import reverse
from wagtail.admin.menu import MenuItem
from wagtail.core import hooks
from django.contrib.auth.models import Permission

from . import admin_urls

try:
    # Django 2
    from django.contrib.staticfiles.templatetags.staticfiles import static
except ImportError:
    # Django 3
    from django.templatetags.static import static


@hooks.register('register_admin_urls')
def register_admin_urls():
    return [
        url(r'^wagtail-transfer/', include(admin_urls, namespace='wagtail_transfer_admin')),
    ]


class WagtailTransferMenuItem(MenuItem):
    def is_shown(self, request):
        return all(
            [
                bool(getattr(settings, "WAGTAILTRANSFER_SOURCES", None)),
                request.user.has_perm("wagtail_transfer.wagtailtransfer_can_import"),
            ]
        )


@hooks.register('register_admin_menu_item')
def register_admin_menu_item():
    return WagtailTransferMenuItem('Import', reverse('wagtail_transfer_admin:choose_page'), classnames='icon icon-doc-empty-inverse', order=10000)


@hooks.register("register_permissions")
def register_wagtail_transfer_permission():
    return Permission.objects.filter(
        content_type__app_label="wagtail_transfer",
        codename="wagtailtransfer_can_import",
    )
