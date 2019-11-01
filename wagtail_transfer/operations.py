import json

from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.core.exceptions import ImproperlyConfigured
from django.utils.functional import cached_property
from wagtail.core.models import Page

from .models import IDMapping


class ImportPlanner:
    def __init__(self, root_page_source_pk, destination_parent_id):
        # Operations that will be performed in this import
        self.operations = []
        self.root_page_source_pk = root_page_source_pk
        self.destination_parent_id = destination_parent_id

        # The set of API records that we have received from the source site,
        # indexed by (model_class, id_from_source_site)
        self.seen_object_data_by_source_pk = {}

        self.unsatisfied_dependencies = set()

        # mapping of (model_class, id_from_source_site) object references to the operations that
        # will create them
        self.satisfied_dependencies = {}

        self.context = ImportContext()

    def add_json_objects_for_import(self, json_data):
        """
        Add the objects in the json to the import plan, as objects that we require to be imported
        """
        data = json.loads(json_data)
        for obj_data in data:
            source_pk = obj_data['pk']

            # locate the model class for this record
            app_label, model_name = obj_data['model'].split('.')
            model = ContentType.objects.get_by_natural_key(app_label, model_name).model_class()

            # index it in seen_object_data_by_source_pk
            self.seen_object_data_by_source_pk[(model, source_pk)] = obj_data

            # TODO: delegate the "choose an operation to handle this object" logic to a helper
            # specific to the model class.
            # Currently the logic below is specific to importing pages.

            # does this object exist at the destination site?
            try:
                mapping = IDMapping.objects.get(uid=obj_data['uid'])
                mapping_exists = True
            except IDMapping.DoesNotExist:
                mapping_exists = False

            if mapping_exists:
                self.context.object_id_mapping[(Page, obj_data['pk'])] = mapping.local_id
                operation = UpdatePage(mapping.content_object, obj_data)
            else:
                if source_pk == self.root_page_source_pk:
                    # this is the root page of the import; ignore the parent ID in the source
                    # record and import at the requested destination instead
                    operation = CreatePage(model, obj_data, self.destination_parent_id)
                else:
                    operation = CreatePage(model, obj_data)

            # page-specific logic ends here

            self.operations.append(operation)

            # update the satisfied_dependencies / unsatisfied_dependencies lists to reflect the
            # objects created by this operation
            for obj_reference in operation.satisfies:
                self.satisfied_dependencies[obj_reference] = operation
                try:
                    self.unsatisfied_dependencies.remove(obj_reference)
                except KeyError:
                    pass

            # update unsatisfied_dependencies with this operation's dependencies
            for obj_reference in operation.dependencies:
                if obj_reference in self.context.object_id_mapping:
                    # this object already exists at the destination
                    pass
                elif obj_reference in self.satisfied_dependencies:
                    # we have already constructed an operation that will create this object
                    pass
                else:
                    # this dependency is not yet satisfied
                    self.unsatisfied_dependencies.add(obj_reference)

    def add_related_json_objects(self, json_data):
        """
        Add the objects in the json to the import plan, as objects that _may_ be imported to
        satisfy dependencies from related objects
        """
        raise NotImplemented

    def run(self):
        if self.unsatisfied_dependencies:
            raise ImproperlyConfigured("Cannot run import until all dependencies are resoved")

        # arrange operations into an order that satisfies dependencies
        operation_order = []
        for operation in self.operations:
            self._add_to_operation_order(operation, operation_order)

        # run operations in order
        with transaction.atomic():
            for operation in operation_order:
                operation.run(self.context)

    def _add_to_operation_order(self, operation, operation_order):
        if operation in operation_order:
            # already in list - no need to add
            return

        for obj_reference in operation.dependencies:
            if obj_reference in self.context.object_id_mapping:
                # this object already exists at the destination - dependency already satisfied
                pass
            else:
                dependency = self.satisfied_dependencies[obj_reference]
                self._add_to_operation_order(dependency, operation_order)

        operation_order.append(operation)


class ImportContext:
    """
    A container for shared data needed during an import, such as the mapping from the source site's
    page IDs to the destination site's IDs. As operations complete, they may add to this data -
    e.g. adding the IDs of newly-created pages
    """
    def __init__(self):
        # dictionary mapping (model_class, source_pk) to destination object PKs
        self.object_id_mapping = {}


class Operation:
    """
    Represents a single database operation to be performed during the data import. This operation
    may depend on other operations to be completed first - for example, creating a page's parent
    page. The import process works by building a dependency graph of operations (which may involve
    multiple calls to the source site's API as new dependencies are encountered, making it
    necessary to retrieve more data), finding a valid sequence to run them in, and running them all
    within a transaction.
    """
    def run(self, context):
        raise NotImplemented

    @cached_property
    def dependencies(self):
        # A list of (model_class, pk_from_source_site) tuples for objects that must exist before we
        # can import this page
        return []

    @cached_property
    def satisfies(self):
        # a list of (model_class, pk_from_source_site) tuples for objects that will be created by
        # this operation
        return []


class CreatePage(Operation):
    def __init__(self, model, object_data, destination_parent_id=None):
        self.model = model
        self.object_data = object_data
        self.destination_parent_id = destination_parent_id

    @cached_property
    def dependencies(self):
        if self.destination_parent_id is None:
            # need to ensure parent page is imported before this one
            return [
                (Page, self.object_data['parent_id']),
            ]
        else:
            return []

    @cached_property
    def satisfies(self):
        return [
            (Page, self.object_data['pk']),
        ]

    def run(self, context):
        if self.destination_parent_id is None:
            # The destination parent ID was not known at the time this operation was built,
            # but should now exist in the page ID mapping
            source_parent_id = self.object_data['parent_id']
            self.destination_parent_id = context.object_id_mapping[(Page, source_parent_id)]

        parent_page = Page.objects.get(id=self.destination_parent_id)

        # Create a page object and populate its attributes from field_data
        self.page = self.model()
        for k, v in self.object_data['fields'].items():
            setattr(self.page, k, v)

        # Add the page to the database as a child of parent_page
        parent_page.add_child(instance=self.page)

        # Add an IDMapping entry for the newly created page
        IDMapping.objects.create(uid=self.object_data['uid'], content_object=self.page)

        # Also add it to object_id_mapping in the context
        source_pk = self.object_data['pk']
        context.object_id_mapping[(Page, source_pk)] = self.page.id


class UpdatePage(Operation):
    def __init__(self, page, object_data):
        self.page = page
        self.object_data = object_data

    def run(self, context):
        # populate page attributes from field_data
        for k, v in self.object_data['fields'].items():
            setattr(self.page, k, v)

        self.page.save()
