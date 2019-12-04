from wagtail.core.blocks import ListBlock, PageChooserBlock, RichTextBlock, StructBlock, ChooserBlock, StreamBlock, BoundBlock, StreamValue

from .richtext import get_reference_handler

def map_over_json(block, stream, func):
    try:
        child_blocks = block.child_blocks
        try:
            for element in stream:
                new_block = child_blocks.get(element['type'])
                new_stream = element['value']
                element['value'] = map_over_json(new_block, new_stream)
        except TypeError:
            for key in stream:
                new_block = child_blocks.get(key)
                new_stream = stream[key]
                stream[key] = map_over_json(new_block, new_stream)
        return stream
    except AttributeError:
        try:
            new_block = block.child_block
            for index, element in enumerate(stream):
                stream[index] = map_over_json(new_block, element)
            return stream
        except AttributeError:
            return func(block, stream)


def get_references_using_handler(block, stream, references):
    references.union(get_block_handler(block).get_object_references(stream))
    return stream

def update_ids_using_handler(block, stream, destination_ids_by_source)
    return get_block_handler(block).update_ids(stream, destination_ids_by_source)



def get_object_references(stream):
    references = set()
    for value, block in iterate_over_base_blocks(stream):
        handler = get_block_handler(block)
        if handler:
            references = references.union(handler.get_object_references(value))

    return references


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


class ChooserBlockHandler(BaseBlockHandler):
    def get_object_references(self, value):
        return {(self.block.target_model, value)}


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
