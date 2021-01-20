import re
from functools import partial

from wagtail.core.rich_text import features
from wagtail.core.rich_text.rewriters import extract_attrs

from .models import get_base_model

FIND_A_TAG = re.compile(r'<a(\b[^>]*)>(.*?)</a>')
FIND_EMBED_TAG = re.compile(r'<embed(\b[^>]*)/>')
FIND_ID = re.compile(r'id="([^"]*)"')


class RichTextReferenceHandler:
    """
    Handles updating ids and retrieving object references for <tag type_attribute="foo" id="my_id" /> tags representing references within rich text. Tags are found using a regex tag_matcher, and their
    specific handler (eg PageLinkHandler) is looked up using a dict, handlers, which maps the value of type_attribute (where type_attribute might be emebedtype)
    to a specific handler.

    The tag matcher must be a compiled regular expression where the first matching group is the tag's body (ie its attributes) and the second the tag's inner contents (if any).
    Note this only works for tags which cannot be nested inside the same tag, so this works fine for eg matching <a> tags since nested <a> tags are illegal.
    """
    def __init__(self, handlers, tag_matcher, type_attribute, destination_ids_by_source={}):
        self.handlers = handlers
        self.tag_matcher = tag_matcher
        self.type_attribute = type_attribute
        self.destination_ids_by_source = destination_ids_by_source

    def update_tag_id(self, match, destination_ids_by_source):
        # Updates a specific tag's id from source to destination Wagtail instance, or removes the tag if no id mapping exists
        tag_body = match.group(1)
        attrs = extract_attrs(tag_body)
        try:
            handler = self.handlers[attrs[self.type_attribute]]
            target_model = get_base_model(handler.get_model())
            new_id = destination_ids_by_source.get((target_model, int(attrs['id'])))
            if new_id is None:
                # Return the tag's inner contents, effectively removing the tag
                try:
                    return match.group(2)
                except IndexError:
                    # The tag has no inner content, return a blank string instead
                    return ''
            # Otherwise update the id and construct the new tag string
            new_tag_body = FIND_ID.sub('id="{0}"'.format(str(new_id)), tag_body)
            tag_body_offset = match.start(0)
            new_tag_string = match.group(0)[:(match.start(1)-tag_body_offset)] + new_tag_body + match.group(0)[(match.end(1)-tag_body_offset):]
            return new_tag_string
        except KeyError:
            # If the relevant handler cannot be found, don't update the tag id
            pass
        return match.group(0)

    def get_objects(self, html):
        # Gets object references
        objects = set()
        if html:
            for match in self.tag_matcher.finditer(html):
                attrs = extract_attrs(match.group(1))
                try:
                    handler = self.handlers[attrs[self.type_attribute]]
                    objects.add((get_base_model(handler.get_model()), int(attrs['id'])))
                except KeyError:
                    # If no handler can be found, no object reference can be added.
                    # This might occur when the link is a plain url
                    pass
        return objects

    def update_ids(self, html, destination_ids_by_source):
        # Update source instance ids to destination instance ids when possible
        if html is None:
            return None
        else:
            return self.tag_matcher.sub(partial(self.update_tag_id, destination_ids_by_source=destination_ids_by_source), html)


class MultiTypeRichTextReferenceHandler:
    """Handles retrieving object references and updating ids for several different kinds of tags in rich text"""
    def __init__(self, handlers):
        self.handlers = handlers

    def update_ids(self, html, destination_ids_by_source):
        for handler in self.handlers:
            html = handler.update_ids(html, destination_ids_by_source)
        return html

    def get_objects(self, html):
        objects = set()
        for handler in self.handlers:
            objects = objects.union(handler.get_objects(html))
        return objects


REFERENCE_HANDLER = None


def get_reference_handler():
    global REFERENCE_HANDLER

    if not REFERENCE_HANDLER:
        embed_handlers = features.get_embed_types()
        link_handlers = features.get_link_types()
        REFERENCE_HANDLER = MultiTypeRichTextReferenceHandler([
            RichTextReferenceHandler(link_handlers, FIND_A_TAG, 'linktype'),
            RichTextReferenceHandler(embed_handlers, FIND_EMBED_TAG, 'embedtype')
        ])
    return REFERENCE_HANDLER
