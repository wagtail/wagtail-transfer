from django.db import models

from wagtail.core.models import Page


class SimplePage(Page):
    intro = models.TextField()


class Advert(models.Model):
    slogan = models.CharField(max_length=255)


class SponsoredPage(Page):
    advert = models.ForeignKey(Advert, blank=True, null=True, on_delete=models.SET_NULL)
    intro = models.TextField()
