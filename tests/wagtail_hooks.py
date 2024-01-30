from wagtail import hooks
from wagtail.rich_text import LinkHandler


class CustomLinkHandler(LinkHandler):
    """
    Custom link handler to test transfer of rich text with custom link types.

    There are situations where a `LinkHandler' subclass might not implement
    the `get_model' method, which we call when processing links - this class
    implements that pattern.
    """
    identifier = "custom-link"

    @classmethod
    def expand_db_attributes(cls, _):
        return '<a href="https://http.cat">'


@hooks.register("register_rich_text_features")
def register_custom_link(features):
    features.register_link_type(CustomLinkHandler)
