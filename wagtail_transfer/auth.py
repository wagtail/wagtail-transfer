import hashlib
import hmac
import re

from django.conf import settings
from django.core.exceptions import PermissionDenied

GROUP_QUERY_WITH_DIGEST = re.compile('(?P<query_before>.*?)&?digest=(?P<digest>[^&]*)(?P<query_after>.*)')

def check_get_digest_wrapper(view_func):
    """
    Check the digest of a request matches its GET parameters
    This is useful when wrapping vendored API views
    """
    def decorated_view(request, *args, **kwargs):
        query_string = request.META.get('QUERY_STRING', '')
        match = GROUP_QUERY_WITH_DIGEST.match(query_string)
        if not match:
            raise PermissionDenied
        digest = match.group('digest')
        message = f'{match.group("query_before")}{match.group("query_after")}'
        if not (digest and message):
            # This decorator is intended for use with GET parameters
            # If there are none, or no digest, something's gone wrong
            raise PermissionDenied
        check_digest(message, digest)

        # Unfortunately the admin API views won't allow unknown GET parameters
        # So we must remove the digest parameter from the request as well
        request.META['QUERY_STRING'] = message

        # Normally request.GET shouldn't be evaluated yet, but in case someone's
        # inspecting it in middleware for example, let's remove the cached version,
        # otherwise it will retain the old digest parameter
        if hasattr(request, 'GET'):
            del request.GET

        response = view_func(request, *args, **kwargs)
        return response
    return decorated_view


def check_digest(message, digest):
    key = settings.WAGTAILTRANSFER_SECRET_KEY

    # Key and message must be bytes objects
    if isinstance(key, str):
        key = key.encode()

    if isinstance(message, str):
        message = message.encode()

    expected_digest = hmac.new(key, message, hashlib.sha1).hexdigest()
    if not hmac.compare_digest(digest, expected_digest):
        raise PermissionDenied


def digest_for_source(source, message):
    key = settings.WAGTAILTRANSFER_SOURCES[source]['SECRET_KEY']

    # Key and message must be bytes objects
    if isinstance(key, str):
        key = key.encode()

    if isinstance(message, str):
        message = message.encode()

    return hmac.new(key, message, hashlib.sha1).hexdigest()
