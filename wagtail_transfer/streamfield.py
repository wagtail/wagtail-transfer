from wagtail.core.blocks import ListBlock, PageChooserBlock, RichTextBlock, StructBlock, ChooserBlock, StreamBlock, BoundBlock, StreamValue

from .richtext import get_reference_handler


def iterate_over_base_blocks(stream):
    for element in stream:
        block = element.block
        if issubclass(type(block), StreamBlock):
            yield from iterate_over_base_blocks(element.value)
        elif issubclass(type(block), StructBlock):
            try:
                yield from iterate_over_base_blocks(element.value.bound_blocks.values())
            except AttributeError:
                yield from iterate_over_base_blocks(element.bound_blocks.values())
        elif issubclass(type(block), ListBlock):
            try:
                yield from iterate_over_base_blocks(element.value)
            except AttributeError:
                for value in element.value:
                    yield (value, block.child_block)
        else:
            yield (element.value, block)


def get_object_references(stream):
    references = set()
    for value, block in iterate_over_base_blocks(stream):
        print(type(block))
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


class RichTextBlockHandler(BaseBlockHandler):
    def get_object_references(self, value):
        return get_reference_handler().get_objects(value)


class ChooserBlockHandler(BaseBlockHandler):
    def get_object_references(self, value):
        return {(self.block.target_model, value.pk)}


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
