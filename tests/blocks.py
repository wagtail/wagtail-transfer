from wagtail.blocks import (CharBlock, IntegerBlock, ListBlock,
                            PageChooserBlock, RichTextBlock, StreamBlock,
                            StructBlock)
from wagtail.documents.blocks import DocumentChooserBlock


class CaptionedPageLink(StructBlock):
    page = PageChooserBlock(required=False)
    text = CharBlock(max_length=250)


# StreamBlocks
class AnotherStreamBlock(StreamBlock):
    page = PageChooserBlock()


class BaseStreamBlock(StreamBlock):
    """
    Define the custom blocks that `StreamField` will utilize
    """

    link_block = CaptionedPageLink()
    integer = IntegerBlock(required=True)
    page = PageChooserBlock()
    stream = AnotherStreamBlock()
    rich_text = RichTextBlock()
    list_of_pages = ListBlock(PageChooserBlock())
    list_of_captioned_pages = ListBlock(CaptionedPageLink())
    document = DocumentChooserBlock()
