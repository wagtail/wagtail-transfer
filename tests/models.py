from django.db import models
from modelcluster.fields import ParentalKey, ParentalManyToManyField
from wagtail.core.fields import RichTextField, StreamField
from wagtail.core.models import Orderable, Page

from .blocks import BaseStreamBlock


class SimplePage(Page):
    intro = models.TextField()


class Advert(models.Model):
    slogan = models.CharField(max_length=255)


class SponsoredPage(Page):
    advert = models.ForeignKey(Advert, blank=True, null=True, on_delete=models.SET_NULL)
    intro = models.TextField()


class SectionedPage(Page):
    intro = models.TextField()


class SectionedPageSection(Orderable):
    page = ParentalKey(SectionedPage, related_name='sections')
    title = models.CharField(max_length=255)
    body = models.TextField()


class PageWithRichText(Page):
    body = RichTextField(max_length=255)


class PageWithStreamField(Page):
    body = StreamField(BaseStreamBlock(), verbose_name="Page body", blank=True)


class PageWithParentalManyToMany(Page):
    ads = ParentalManyToManyField(Advert)
