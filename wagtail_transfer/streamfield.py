from functools import partial

from wagtail.core.blocks import (ChooserBlock, ListBlock, RichTextBlock, StreamBlock,
                                 StructBlock)

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
    stream_block_handler.map_over_json(stream, get_references)
    return references


def update_object_ids(stream_block, stream, destination_ids_by_source):
    """Loops over list-of-dicts formatted StreamField (stream) to update object references. This format is used as opposed
    to the StreamChild object format to prevent ChooserBlocks trying to load nonexistent models with old ids upon to_python
    being called"""
    update_ids = partial(update_ids_using_handler, destination_ids_by_source=destination_ids_by_source)
    stream_block_handler = get_block_handler(stream_block)
    updated_stream = stream_block_handler.map_over_json(stream, update_ids)
    return updated_stream


class BaseBlockHandler:
    """Base class responsible for finding object references and updating ids for StreamField blocks"""
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
        list of dicts (imported json) format.
        """
        return func(self.block, stream)


class ListBlockHandler(BaseBlockHandler):
    def map_over_json(self, stream, func):
        new_block = self.block.child_block
        new_block_handler = get_block_handler(new_block)
        for index, element in enumerate(stream):
            stream[index] = new_block_handler.map_over_json(element, func)
        return stream


class StreamBlockHandler(BaseBlockHandler):
    def map_over_json(self, stream, func):
        for element in stream:
            new_block = self.block.child_blocks.get(element['type'])
            new_block_handler = get_block_handler(new_block)
            new_stream = element['value']
            element['value'] = new_block_handler.map_over_json(new_stream, func)
        return stream


class StructBlockHandler(BaseBlockHandler):
    def map_over_json(self, stream, func):
        for key in stream:
            new_block = self.block.child_blocks.get(key)
            new_block_handler = get_block_handler(new_block)
            new_stream = stream[key]
            stream[key] = new_block_handler.map_over_json(new_stream, func)
        return stream


class RichTextBlockHandler(BaseBlockHandler):
    def get_object_references(self, value):
        return get_reference_handler().get_objects(value)

    def update_ids(self, value, destination_ids_by_source):
        value = get_reference_handler().update_ids(value, destination_ids_by_source)
        return value


class ChooserBlockHandler(BaseBlockHandler):
    def get_object_references(self, value):
        if value:
            return {(self.block.target_model, value)}
        return set()

    def update_ids(self, value, destination_ids_by_source):
        value = destination_ids_by_source.get((self.block.target_model, value), value)
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
