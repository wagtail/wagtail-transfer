import hashlib
import hmac

from django.conf import settings
from django.core.exceptions import PermissionDenied


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
