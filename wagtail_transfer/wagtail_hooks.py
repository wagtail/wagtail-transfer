from django.conf import settings
from django.contrib.auth.models import Permission
from django.templatetags.static import static
from django.urls import include, path, reverse
from wagtail import VERSION as WAGTAIL_VERSION
from wagtail import hooks
from wagtail.admin.menu import MenuItem

from . import admin_urls


@hooks.register('register_admin_urls')
def register_admin_urls():
    return [
        path('wagtail-transfer/', include(admin_urls, namespace='wagtail_transfer_admin')),
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
    return WagtailTransferMenuItem(
        'Import',
        reverse('wagtail_transfer_admin:choose_page'),
        order=10000,
        classname="icon icon-doc-empty-inverse",
    )


@hooks.register("register_permissions")
def register_wagtail_transfer_permission():
    return Permission.objects.filter(
        content_type__app_label="wagtail_transfer",
        codename="wagtailtransfer_can_import",
    )
