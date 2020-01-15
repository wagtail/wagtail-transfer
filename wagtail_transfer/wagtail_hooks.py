from django.conf import settings
from django.conf.urls import url, include
from django.contrib.staticfiles.templatetags.staticfiles import static
from django.urls import reverse
from django.utils.html import format_html

from wagtail.admin.menu import MenuItem
from wagtail.core import hooks

from . import admin_urls


@hooks.register('register_admin_urls')
def register_admin_urls():
    return [
        url(r'^wagtail-transfer/', include(admin_urls, namespace='wagtail_transfer_admin')),
    ]


class WagtailTransferMenuItem(MenuItem):
    def is_shown(self, request):
        return bool(getattr(settings, 'WAGTAILTRANSFER_SOURCES', None))


@hooks.register('register_admin_menu_item')
def register_admin_menu_item():
    return WagtailTransferMenuItem('Import pages', reverse('wagtail_transfer_admin:choose_page'), classnames='icon icon-doc-empty-inverse', order=10000)
