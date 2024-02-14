from wagtail import hooks
from wagtail.rich_text import LinkHandler


class CustomLinkHandler(LinkHandler):
    """
    Custom link handler to test transfer of rich text with custom link types.

    There are situations where a `LinkHandler' subclass might not implement
    the `get_model' method, which we call when processing links - this class
    implements that pattern.
    """

    identifier = "custom-link-notimplemented"

    @classmethod
    def expand_db_attributes(cls, _):
        return '<a href="https://notimplemented.com">'


class CustomLinkHandlerNoneModel(LinkHandler):
    """
    Custom link handler to test transfer of rich text with custom link types.

    Used for testing the case that the `get_model' method returns None.
    """

    identifier = "custom-link-none"

    @staticmethod
    def get_model():
        return None

    @classmethod
    def expand_db_attributes(cls, _):
        return '<a href="https://none.com">'


@hooks.register("register_rich_text_features")
def register_custom_links(features):
    features.register_link_type(CustomLinkHandler)
    features.register_link_type(CustomLinkHandlerNoneModel)
