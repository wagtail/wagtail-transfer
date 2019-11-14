from django.conf.urls import url, include

from wagtail.core import hooks

from . import admin_urls


@hooks.register('register_admin_urls')
def register_admin_urls():
    return [
        url(r'^wagtail-transfer/', include(admin_urls, namespace='wagtail_transfer_admin')),
    ]
