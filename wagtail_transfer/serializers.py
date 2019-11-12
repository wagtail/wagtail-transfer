from django.utils.encoding import is_protected_type

# FIXME: work out how to filter out all OneToOneFields with parent_link=True, rather than special-casing page_ptr
IGNORED_PAGE_ATTRS = ['id', 'path', 'depth', 'numchild', 'url_path', 'content_type', 'page_ptr']


def serialize_page_fields(page):
    field_data = {}
    for field in page._meta.get_fields():
        if not hasattr(field, 'attname'):
            continue

        if field.name in IGNORED_PAGE_ATTRS:
            continue

        value = field.value_from_object(page)
        if not is_protected_type(value):
            value = field.value_to_string(page)

        field_data[field.name] = value

    return field_data
