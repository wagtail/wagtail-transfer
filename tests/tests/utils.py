from wagtail import VERSION as WAGTAIL_VERSION


def has_new_listblock_format():
    major, minor, *_ = WAGTAIL_VERSION
    return major > 2 or (major == 2 and minor > 15)