from django.db import models
from django.db.models.fields.reverse_related import ManyToOneRel
from django.utils.encoding import is_protected_type

from wagtail.core.fields import RichTextField
from wagtail.core.rich_text.feature_registry import FeatureRegistry

from .models import get_base_model


class FieldAdapter:
    def __init__(self, field):
        self.field = field
        self.name = self.field.name

    def serialize(self, instance):
        """
        Retrieve the value for this field from the given model instance, and return a
        representation of it that can be included in JSON data
        """
        value = self.field.value_from_object(instance)
        if not is_protected_type(value):
            value = self.field.value_to_string(instance)

        return value

    def get_object_references(self, instance):
        """
        Return a set of (model_class, id) pairs for all objects referenced in this field
        """
        return set()


class ForeignKeyAdapter(FieldAdapter):
    def __init__(self, field):
        super().__init__(field)
        self.related_base_model = get_base_model(self.field.related_model)

    def get_object_references(self, instance):
        pk = self.field.value_from_object(instance)
        if pk is None:
            return set()
        else:
            return {(self.related_base_model, pk)}


class ManyToOneRelAdapter(FieldAdapter):
    def __init__(self, field):
        super().__init__(field)
        self.related_field = field.field
        self.related_model = field.related_model

        from .serializers import get_model_serializer
        self.related_model_serializer = get_model_serializer(self.related_model)

    def _get_related_objects(self, instance):
        return getattr(instance, self.name).all()

    def serialize(self, instance):
        return [
            self.related_model_serializer.serialize(obj)
            for obj in self._get_related_objects(instance)
        ]

    def get_object_references(self, instance):
        refs = set()
        for obj in self._get_related_objects(instance):
            refs.update(self.related_model_serializer.get_object_references(obj))
        return refs

features = FeatureRegistry()

import re

FIND_A_TAG = re.compile(r'<a(\b[^>]*)>')
FIND_EMBED_TAG = re.compile(r'<embed(\b[^>]*)/>')
FIND_ATTRS = re.compile(r'([\w-]+)\="([^"]*)"')
FIND_ID = re.compile(r'id="([^"]*)"')


def extract_attrs(attr_string):
    """
    helper method to extract tag attributes, as a dict of un-escaped strings
    """
    attributes = {}
    for name, val in FIND_ATTRS.findall(attr_string):
        val = val.replace('&lt;', '<').replace('&gt;', '>').replace('&quot;', '"').replace('&amp;', '&')
        attributes[name] = val
    return attributes


class EmbedRewriter:
    """
    Rewrites <embed embedtype="foo" /> tags within rich text into the HTML fragment given by the
    embed rule for 'foo'. Each embed rule is a function that takes a dict of attributes and
    returns the HTML fragment.
    """
    def __init__(self, embed_rules):
        self.embed_rules = embed_rules

    def replace_tag(self, match):
        attrs = extract_attrs(match.group(1))
        try:
            rule = self.embed_rules[attrs['embedtype']]
            target_model = get_base_model(rule.get_model())
            new_id = self.context.destination_ids_by_source[(target_model, rule.get_instance(attrs).id)]
            return FIND_ID.sub('id="{0}"'.format(str(new_id)), match.group(0))
        except KeyError:
            pass
        return match.group(0)

    def objects(self, html):
        objects = set()
        for match in FIND_EMBED_TAG.finditer(html):
            attrs = extract_attrs(match.group(1))
            try:
                rule = self.embed_rules[attrs['embedtype']]
                objects.add((get_base_model(rule.get_model()), rule.get_instance(attrs).id))
            except KeyError:
                # silently drop any tags with an unrecognised or missing embedtype attribute
                pass
        return objects

    def __call__(self, html, context):
        self.context = context
        return FIND_EMBED_TAG.sub(self.replace_tag, html)


class LinkRewriter:
    """
    Rewrites <a linktype="foo"> tags within rich text into the HTML fragment given by the
    rule for 'foo'. Each link rule is a function that takes a dict of attributes and
    returns the HTML fragment for the opening tag (only).
    """
    def __init__(self, link_rules):
        self.link_rules = link_rules

    def replace_tag(self, match):
        attrs = extract_attrs(match.group(1))
        try:
            rule = self.link_rules[attrs['linktype']]
            target_model = get_base_model(rule.get_model())
            new_id = self.context.destination_ids_by_source[(target_model, rule.get_instance(attrs).id)]
            return FIND_ID.sub('id="{0}"'.format(str(new_id)), match.group(0))
        except KeyError:
            pass
        return match.group()

    def objects(self, html):
        objects = set()
        for match in FIND_A_TAG.finditer(html):
            attrs = extract_attrs(match.group(1))
            try:
                rule = self.link_rules[attrs['linktype']]
                objects.add((get_base_model(rule.get_model()), rule.get_instance(attrs).id))
            except KeyError:
                # silently drop any tags with an unrecognised or missing embedtype attribute
                pass
        return objects

    def __call__(self, html, context):
        self.context = context
        return FIND_A_TAG.sub(self.replace_tag, html)


class MultiRuleRewriter:
    """Rewrites HTML by applying a sequence of rewriter functions"""
    def __init__(self, rewriters):
        self.rewriters = rewriters

    def __call__(self, html, context):
        for rewrite in self.rewriters:
            html = rewrite(html, context)
        return html

    def objects(self, html):
        objects = set()
        for rewrite in self.rewriters:
            objects = objects.union(rewrite.objects(html))
        return objects


embed_rules = features.get_embed_types()
link_rules = features.get_link_types()
rewriter = MultiRuleRewriter([
        LinkRewriter({linktype: handler for linktype, handler in link_rules.items()}),
        EmbedRewriter({embedtype: handler for embedtype, handler in embed_rules.items()})
        ])



class RichTextAdapter(FieldAdapter):

    def get_object_references(self, instance):
        """
        Return a set of (model_class, id) pairs for all objects referenced in this field
        """
        return rewriter.objects(self.field.value_from_object(instance))



ADAPTERS_BY_FIELD_CLASS = {
    models.Field: FieldAdapter,
    models.ForeignKey: ForeignKeyAdapter,
    ManyToOneRel: ManyToOneRelAdapter,
    RichTextField: RichTextAdapter
}


def get_field_adapter(field):
    # find the adapter class for the most specific class in the field's inheritance tree
    for field_class in type(field).__mro__:
        if field_class in ADAPTERS_BY_FIELD_CLASS:
            adapter_class = ADAPTERS_BY_FIELD_CLASS[field_class]
            return adapter_class(field)

    raise ValueError("No adapter found for field: %r" % field)
