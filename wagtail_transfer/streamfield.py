from functools import partial

from django.core.exceptions import ValidationError
from wagtail.blocks import (ChooserBlock, ListBlock, RichTextBlock,
                            StreamBlock, StructBlock)

from .models import get_base_model
from .richtext import get_reference_handler


def get_references_using_handler(block, stream, references):
    """Gets object references from a streamfield with block object block and value stream, and updates the reference
    set with the result"""
    block_handler = get_block_handler(block)
    references.update(block_handler.get_object_references(stream))
    return stream


def update_ids_using_handler(block, stream, destination_ids_by_source):
    """Updates reference ids from source to destination site for a streamfield block, using its handler"""
    block_handler = get_block_handler(block)
    return block_handler.update_ids(stream, destination_ids_by_source)


def get_object_references(stream_block, stream):
    """Loops over list of dicts formatted StreamField (stream) to find object references. This format is used as opposed
    to the StreamChild object format to prevent ChooserBlocks trying to load nonexistent models with old ids upon to_python
    being called"""
    references = set()
    get_references = partial(get_references_using_handler, references=references)
    stream_block_handler = get_block_handler(stream_block)
    try:
        stream_block_handler.map_over_json(stream, get_references)
    except ValidationError:
        pass
    return references


def update_object_ids(stream_block, stream, destination_ids_by_source):
    """Loops over list-of-dicts formatted StreamField (stream) to update object references. This format is used as opposed
    to the StreamChild object format to prevent ChooserBlocks trying to load nonexistent models with old ids upon to_python
    being called"""
    update_ids = partial(update_ids_using_handler, destination_ids_by_source=destination_ids_by_source)
    stream_block_handler = get_block_handler(stream_block)
    try:
        updated_stream = stream_block_handler.map_over_json(stream, update_ids)
    except ValidationError:
        updated_stream = []
    return updated_stream


class BaseBlockHandler:
    """Base class responsible for finding object references and updating ids for StreamField blocks"""

    empty_value = None

    def __init__(self, block):
        self.block = block

    def get_object_references(self, value):
        """
        Return a set of (model_class, id) pairs for all objects referenced in this block
        """
        return set()

    def update_ids(self, value, destination_ids_by_source):
        """
        Update source site ids to destination site ids
        """
        return value

    def map_over_json(self, stream, func):
        """
        Apply a function, func, to each of the base blocks' values (ie not Struct, List, Stream) of a StreamField in
        list of dicts (imported json) format and return a copy of the rewritten streamfield.
        """
        value = func(self.block, stream)
        if self.block.required and value is None:
            raise ValidationError('This block requires a value')
        return value


class ListBlockHandler(BaseBlockHandler):
    def map_over_json(self, stream, func):
        updated_stream = []
        new_block = self.block.child_block
        new_block_handler = get_block_handler(new_block)
        block_is_in_new_format = getattr(
            self.block,
            "_item_is_in_block_format",
            lambda x: False
        )
        for element in stream:
            try:
                if block_is_in_new_format(element):
                    # We are dealing with new-style ListBlock representation
                    new_value = new_block_handler.map_over_json(element['value'], func)
                    updated_stream.append({'type': element['type'], 'value': new_value, 'id': element['id']})
                else:
                    new_value = new_block_handler.map_over_json(element, func)
                    updated_stream.append(new_value)
            except ValidationError:
                pass
        return updated_stream

    @property
    def empty_value(self):
        return []


class StreamBlockHandler(BaseBlockHandler):
    def map_over_json(self, stream, func):
        updated_stream = []
        for element in stream:
            new_block = self.block.child_blocks.get(element['type'])
            new_block_handler = get_block_handler(new_block)
            new_stream = element['value']
            try:
                new_value = new_block_handler.map_over_json(new_stream, func)
                updated_stream.append({'type': element['type'], 'value': new_value, 'id': element['id']})
            except ValidationError:
                # Omit the block if a required field was left blank due to the import
                pass
        if self.block.required and not updated_stream:
            raise ValidationError('This block requires a value')
        return updated_stream

    @property
    def empty_value(self):
        return []


class StructBlockHandler(BaseBlockHandler):
    remove_if_empty = True

    def map_over_json(self, stream, func):
        updated_stream = {}
        for key in stream:
            new_block = self.block.child_blocks.get(key)
            new_block_handler = get_block_handler(new_block)
            new_stream = stream[key]
            try:
                new_value = new_block_handler.map_over_json(new_stream, func)
            except ValidationError:
                if new_block.required:
                    raise ValidationError('This block requires a value for {}'.format(new_block))
                else:
                    # If the new block isn't required, just set it to the empty value
                    new_value = new_block_handler.empty_value
            updated_stream[key] = new_value
        return updated_stream


class RichTextBlockHandler(BaseBlockHandler):
    def get_object_references(self, value):
        return get_reference_handler().get_objects(value)

    def update_ids(self, value, destination_ids_by_source):
        value = get_reference_handler().update_ids(value, destination_ids_by_source)
        return value


class ChooserBlockHandler(BaseBlockHandler):
    def get_object_references(self, value):
        if value:
            return {(get_base_model(self.block.model_class), value)}
        return set()

    def update_ids(self, value, destination_ids_by_source):
        value = destination_ids_by_source.get((get_base_model(self.block.model_class), value))
        return value


def get_block_handler(block):
    # find the handler class for the most specific class in the block's inheritance tree
    for block_class in type(block).__mro__:
        if block_class in HANDLERS_BY_BLOCK_CLASS:
            handler_class = HANDLERS_BY_BLOCK_CLASS[block_class]
            return handler_class(block)
    return BaseBlockHandler(block)


HANDLERS_BY_BLOCK_CLASS = {
    RichTextBlock: RichTextBlockHandler,
    ChooserBlock: ChooserBlockHandler,
    ListBlock: ListBlockHandler,
    StreamBlock: StreamBlockHandler,
    StructBlock: StructBlockHandler,
}
