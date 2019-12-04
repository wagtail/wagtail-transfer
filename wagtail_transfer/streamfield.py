from wagtail.core.blocks import ListBlock, PageChooserBlock, RichTextBlock, StructBlock, ChooserBlock, StreamBlock, BoundBlock, StreamValue

from .richtext import get_reference_handler
from functools import partial


def map_over_json(block, stream, func):
    try:
        child_blocks = block.child_blocks
        try:
            for element in stream:
                new_block = child_blocks.get(element['type'])
                new_stream = element['value']
                element['value'] = map_over_json(new_block, new_stream, func)
        except TypeError:
            for key in stream:
                new_block = child_blocks.get(key)
                new_stream = stream[key]
                stream[key] = map_over_json(new_block, new_stream, func)
        return stream
    except AttributeError:
        try:
            new_block = block.child_block
            for index, element in enumerate(stream):
                stream[index] = map_over_json(new_block, element, func)
            return stream
        except AttributeError:
            return func(block, stream)


def get_references_using_handler(block, stream, references):
    block_handler = get_block_handler(block)
    if block_handler:
        references.union(block_handler.get_object_references(stream))
    return stream


def update_ids_using_handler(block, stream, destination_ids_by_source):
    block_handler = get_block_handler(block)
    if block_handler:
        return block_handler.update_ids(stream, destination_ids_by_source)
    else:
        return stream


def get_object_references(stream_block, stream):
    references = set()
    get_references = partial(get_references_using_handler, references=references)
    map_over_json(stream_block, stream, get_references)
    return references


def update_object_ids(stream_block, stream, destination_ids_by_source):
    update_ids = partial(update_ids_using_handler, destination_ids_by_source=destination_ids_by_source)
    updated_stream = map_over_json(stream_block, stream, update_ids)
    return updated_stream


class BaseBlockHandler:
    def __init__(self, block):
        self.block = block

    def get_object_references(self, value):
        """
        Return a set of (model_class, id) pairs for all objects referenced in this block
        """
        return set()

    def update_ids(self, value, destination_ids_by_source):
        return value


class RichTextBlockHandler(BaseBlockHandler):
    def get_object_references(self, value):
        return get_reference_handler().get_objects(value)

    def update_ids(self, value, destination_ids_by_source):
        value = get_reference_handler().update_ids(value, destination_ids_by_source)
        return value


class ChooserBlockHandler(BaseBlockHandler):
    def get_object_references(self, value):
        return {(self.block.target_model, value)}

    def update_ids(self, value, destination_ids_by_source):
        value = destination_ids_by_source.get((self.block.target_model, value), value)
        return value


def get_block_handler(block):
    # find the handler class for the most specific class in the block's inheritance tree
    for block_class in type(block).__mro__:
        if block_class in HANDLERS_BY_BLOCK_CLASS:
            handler_class = HANDLERS_BY_BLOCK_CLASS[block_class]
            return handler_class(block)
    return None


HANDLERS_BY_BLOCK_CLASS = {
    RichTextBlock: RichTextBlockHandler,
    ChooserBlock: ChooserBlockHandler,
}
