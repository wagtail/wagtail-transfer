from django.db import models
from modelcluster.fields import ParentalKey, ParentalManyToManyField
from taggit.managers import TaggableManager
from wagtail.core.fields import RichTextField, StreamField
from wagtail.core.models import Orderable, Page
from wagtail.snippets.models import register_snippet

from .blocks import BaseStreamBlock


class SimplePage(Page):
    intro = models.TextField()


class Advert(models.Model):
    slogan = models.CharField(max_length=255)
    tags = TaggableManager()
    run_from = models.DateField(blank=True, null=True)
    run_until = models.DateTimeField()


class LongAdvert(Advert):
    description = models.TextField()


class Author(models.Model):
    name = models.CharField(max_length=255)
    bio = models.TextField()


@register_snippet
class Category(models.Model):
    name = models.CharField(max_length=255, unique=True)
    colour = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return "{} {}".format(self.colour, self.name)


class SponsoredPage(Page):
    advert = models.ForeignKey(Advert, blank=True, null=True, on_delete=models.SET_NULL)
    author = models.ForeignKey(Author, blank=True, null=True, on_delete=models.SET_NULL)
    intro = models.TextField()
    categories = ParentalManyToManyField(Category)


class SectionedPage(Page):
    intro = models.TextField()


class SectionedPageSection(Orderable):
    page = ParentalKey(SectionedPage, related_name='sections')
    title = models.CharField(max_length=255)
    body = models.TextField()


class PageWithRichText(Page):
    body = RichTextField(max_length=255, blank=True, null=True)


class PageWithStreamField(Page):
    body = StreamField(BaseStreamBlock(), verbose_name="Page body", blank=True)


class PageWithParentalManyToMany(Page):
    ads = ParentalManyToManyField(Advert)


class ModelWithManyToMany(models.Model):
    ads = models.ManyToManyField(Advert)


class Avatar(models.Model):
    image = models.ImageField(upload_to='avatars')


class RedirectPage(Page):
    redirect_to = models.ForeignKey(Page, blank=False, null=False, on_delete=models.PROTECT, related_name='+')


class PageWithRelatedPages(Page):
    related_pages = models.ManyToManyField(Page, related_name='+')
