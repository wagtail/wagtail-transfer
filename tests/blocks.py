from wagtail.core.blocks import (
    CharBlock, RichTextBlock, StreamBlock, StructBlock, ListBlock, PageChooserBlock
)


class CaptionedPageLink(StructBlock):
    page = PageChooserBlock()
    text = CharBlock(max_length=250)


# StreamBlocks
class AnotherStreamBlock(StreamBlock):
    page = PageChooserBlock()


class BaseStreamBlock(StreamBlock):
    """
    Define the custom blocks that `StreamField` will utilize
    """
    link_block = CaptionedPageLink()
    page = PageChooserBlock()
    stream = AnotherStreamBlock()
    rich_text = RichTextBlock()
    list_of_pages = ListBlock(PageChooserBlock())
