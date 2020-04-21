import hashlib
from contextlib import contextmanager

import requests
from django.core.files.base import ContentFile

from .models import ImportedFile


@contextmanager
def open_file(field, file):
    # Open file if it is closed
    close_file = False
    f = file

    if file.closed:
        # Reopen the file

        # First check if the file is stored on the local filesystem
        try:
            file.path

            is_local = True
        except NotImplementedError:
            is_local = False

        if is_local:
            f.open('rb')
        else:
            # Some external storage backends don't allow reopening
            # the file. Get a fresh file instance. #1397
            storage = field.storage
            f = storage.open(f.name, 'rb')

        close_file = True

    # Seek to beginning
    f.seek(0)

    try:
        yield f
    finally:
        if close_file:
            f.close()


def get_file_size(field, instance):
    """
    Gets the size of the file in the given field on the given instance.
    """
    # Cases we know about
    from wagtail.documents.models import AbstractDocument
    from wagtail.images.models import AbstractImage
    if isinstance(instance, (AbstractDocument, AbstractImage)) and field.name == 'file':
        return instance.get_file_size()

    # Allow developers to provide a file size getter for custom file fields
    # TODO: complete, test and document this mechanism
    # size_getter = getattr(instance, 'wagtailtransfer_get_{}_size', None)
    # if size_getter:
    #     return size_getter()

    # Fall back to asking Django
    # This is potentially very slow as it may result in a call to an external storage service
    return field.value_from_object(instance).size


def get_file_hash(field, instance):
    """
    Gets the SHA1 hash of the file in the given field on the given instance.
    """
    # Cases we know about
    from wagtail.documents.models import AbstractDocument
    from wagtail.images.models import AbstractImage
    if isinstance(instance, (AbstractDocument, AbstractImage)) and field.name == 'file':
        return instance.get_file_hash()

    # Allow developers to provide a file hash getter for custom file fields
    # TODO: complete, test and document this mechanism
    # hash_getter = getattr(instance, 'wagtailtransfer_get_{}_hash', None)
    # if hash_getter:
    #     return hash_getter()

    # Fall back to calculating it on the fly
    with open_file(field, field.value_from_object(instance)) as f:
        return hashlib.sha1(f.read()).hexdigest()


class FileTransferError(Exception):
    pass


class File:
    """
    Represents a file that needs to be imported

    Note that local_filename is only a guideline, it may be changed to avoid conflict with an existing file
    """
    def __init__(self, local_filename, size, hash, source_url):
        self.local_filename = local_filename
        self.size = size
        self.hash = hash
        self.source_url = source_url

    def transfer(self):
        response = requests.get(self.source_url)

        if response.status_code != 200:
            raise FileTransferError("Non-200 response from image URL")

        return ImportedFile.objects.create(
            file=ContentFile(response.content, name=self.local_filename),
            source_url=self.source_url,
            hash=self.hash,
            size=self.size,
        )

    def __hash__(self):
        return hash((self.local_filename, self.size, self.hash, self.source_url))
