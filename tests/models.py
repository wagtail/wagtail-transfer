from django.db import models

from wagtail.core.models import Page


class SimplePage(Page):
    intro = models.TextField()
