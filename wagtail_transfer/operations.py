import json

from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.core.exceptions import ImproperlyConfigured
from django.utils.functional import cached_property
from wagtail.core.models import Page

from .models import IDMapping


class ImportPlanner:
    def __init__(self, root_page_source_pk, destination_parent_id):

        self.root_page_source_pk = root_page_source_pk
        self.destination_parent_id = destination_parent_id

        # A mapping of objects on the source site to their IDs on the destination site.
        # Keys are tuples of (model_class, source_id); values are destination IDs.
        # model_class must be the highest concrete model in the inheritance tree - i.e.
        # Page, not BlogPage
        self.destination_ids_by_source = {}

        # An objective describes a state that we want to reach, e.g.
        # "page 123 must exist at the destination in its most up-to-date form". This is represented
        # as a tuple of (model_class, source_id, objective_type), where objective_type is one of:
        # 'exists': achieved when the object exists at the destination site and is listed in
        #           destination_ids_by_source
        # 'updated': achieved when the object exists at the destination site, with any data updates
        #            from the source site applied, and is listed in destination_ids_by_source
        # 'located': achieved when the object has been confirmed to exist at the destination and
        #            listed in destination_ids_by_source, OR confirmed not to exist at the
        #            destination
        self.objectives = set()

        # objectives that have not yet been converted into tasks
        self.unhandled_objectives = set()

        # a mapping of objects on the source site to their UIDs.
        # Keys are tuples of (model_class, source_id); values are UIDs.
        self.uids_by_source = {}

        # a mapping of objects on the source site to their field data
        self.object_data_by_source = {}

        # A task describes something that needs to happen to reach an objective, e.g.
        # "create page 123". This is represented as a tuple of (model_class, source_id, action),
        # where action is 'create' or 'update'

        # tasks that will be performed in this import
        self.tasks = set()
        # tasks that require us to fetch object data before we can convert them into operations.
        self.postponed_tasks = set()
        # objects we need to fetch to satisfy postponed_tasks, expressed as (model_class, source_id)
        self.missing_object_data = set()

        # Mapping from objectives to operations that satisfy that objective. If the objective
        # does not require any action (e.g. it's an 'ensure exists' on an object that already
        # exists), the value is None.
        # A task can be converted into an operation once all the object data relating to it has
        # been fetched. An operation is an object with a `run` method which accomplishes the task.
        # It also has a list of dependencies - objectives that must be completed before the `run`
        # method can be called.
        self.resolutions = {}

        # Mapping from tasks to operations that perform the task
        self.task_resolutions = {}

    def _model_for_path(self, model_path):
        """
        Given an 'app_name.model_name' string, return the model class
        """
        app_label, model_name = model_path.split('.')
        return ContentType.objects.get_by_natural_key(app_label, model_name).model_class()

    def _base_model_for_path(self, model_path):
        """
        Given an 'app_name.model_name' string, return the Model class for the base model
        (e.g. for 'blog.blog_page', return Page)
        """
        model = self._model_for_path(model_path)

        # ensure we're using the base model (i.e. Page rather than BlogPage)
        if model._meta.parents:
            model = model._meta.get_parent_list()[0]

        return model

    def add_json(self, json_data):
        """
        Add JSON data to the import plan. The data is a dict consisting of:
        'ids_for_import': a list of [source_id, model_classname] pairs for the set of objects
            explicitly requested to be imported. (For example, in a page import, this is the set of
            descendant pages of the selected root page.)
        'mappings': a list of mappings between UIDs and the object IDs that exist on the source
            site, each mapping being expressed as the list
            ['appname.model_classname', source_id, uid].
            All object references that appear in 'objects' (as foreign keys, rich text, streamfield
            or anything else) must have an entry in this mappings table, unless the API on the
            source side is able to determine with certaintly that the destination importer will not
            use it (e.g. it is the parent page of the imported root page).
        'objects': a list of dicts containing full object data used for creating or updating object
            records. This may include additional objects beyond the ones listed in ids_for_import,
            to assist in resolving related objects.
        """
        data = json.loads(json_data)

        # add source id -> uid mappings to the uids_by_source dict
        for model_path, source_id, uid in data['mappings']:
            model = self._base_model_for_path(model_path)
            self.uids_by_source[(model, source_id)] = uid

        # add object data to the object_data_by_source dict
        for obj_data in data['objects']:
            model = self._base_model_for_path(obj_data['model'])
            source_id = obj_data['pk']
            self.object_data_by_source[(model, source_id)] = obj_data

        # retry tasks that were previously postponed due to missing object data
        self._retry_tasks()

        # for each ID in the import list, add an objective to specify that we want an up-to-date
        # copy of that object on the destination site
        for model_path, source_id in data['ids_for_import']:
            model = self._base_model_for_path(model_path)
            objective = (model, source_id, 'updated')

            # add to the set of objectives that need handling, unless it's one we've already seen
            # (in which case it's either in the queue to be handled, or has been handled already)
            if objective not in self.objectives:
                self.objectives.add(objective)
                self.unhandled_objectives.add(objective)

        # Process all unhandled objectives - which may trigger new objectives as dependencies of
        # the resulting operations - until no unhandled objectives remain
        while self.unhandled_objectives:
            objective = self.unhandled_objectives.pop()
            self._handle_objective(objective)

    def _handle_objective(self, objective):
        model, source_id, objective_type = objective

        # look up uid for this item;
        # the export API is expected to supply the id->uid mapping for all referenced objects,
        # so this lookup should always succeed (and if it doesn't, we leave the KeyError uncaught)
        uid = self.uids_by_source[(model, source_id)]

        # look for a matching uid on the destination site
        try:
            mapping = IDMapping.objects.get(uid=uid)
        except IDMapping.DoesNotExist:
            mapping = None

        if mapping:
            self.destination_ids_by_source[(model, source_id)] = mapping.local_id

        if objective_type == 'located':
            # for this objective, we are only required to find the corresponding destination ID
            # or determine that there isn't one - so there is no further action
            task = None

        elif objective_type == 'exists':
            if mapping:
                # object exists; no further action
                task = None
            else:
                # object does not exist locally; need to create it
                task = (model, source_id, 'create')

        elif objective_type == 'updated':
            if mapping:
                # object exists locally, but we need to update it
                task = (model, source_id, 'update')
            else:
                # object does not exist locally; need to create it
                task = (model, source_id, 'create')

        else:
            raise ValueError("Unrecognised objective type: %r" % objective_type)

        if task:
            self._handle_task(objective, task)
        else:
            self.resolutions[objective] = None

    def _handle_task(self, objective, task):
        """
        Attempt to convert a task into a corresponding operation.May fail if we do not yet have
        the object data for this object, in which case it will be added to postponed_tasks
        """

        # It's possible that we've already found a resolution for this task in the process of
        # solving another objective; for example, "ensure page 123 exists" and "ensure page 123
        # is fully updated" might both be solved by creating page 123. If so, we re-use the
        # same operation that we built previously; this ensures that when we establish an order
        # for the operations to happen in, we'll recognise the duplicate and won't run it twice.
        try:
            operation = self.task_resolutions[task]
            self.resolutions[objective] = operation
            return
        except KeyError:
            pass

        model, source_id, action = task
        try:
            object_data = self.object_data_by_source[(model, source_id)]
        except KeyError:
            # need to postpone this until we have the object data
            self.postponed_tasks.add((objective, task))
            self.missing_object_data.add((model, source_id))
            return

        # retrieve the specific model for this object
        specific_model = self._model_for_path(object_data['model'])

        if action == 'create':
            if source_id == self.root_page_source_pk:
                # this is the root page of the import; ignore the parent ID in the source
                # record and import at the requested destination instead
                operation = CreatePage(specific_model, object_data, self.destination_parent_id)
            else:
                operation = CreatePage(specific_model, object_data)
        else:  # action == 'update'
            destination_id = self.destination_ids_by_source[(model, source_id)]
            obj = specific_model.objects.get(pk=destination_id)
            operation = UpdatePage(obj, object_data)

        self.resolutions[objective] = operation

        for objective in operation.dependencies:
            if objective not in self.objectives:
                self.objectives.add(objective)
                self.unhandled_objectives.add(objective)

    def _retry_tasks(self):
        """
        Retry tasks that were previously postponed due to missing object data
        """
        previous_postponed_tasks = self.postponed_tasks
        self.postponed_tasks = set()

        # FIXME: move this to the place where we make the subsequent API fetch
        self.missing_object_data.clear()

        for objective, task in previous_postponed_tasks:
            self._handle_task(objective, task)

    def run(self):
        if self.unhandled_objectives or self.postponed_tasks:
            raise ImproperlyConfigured("Cannot run import until all dependencies are resoved")

        context = ImportContext(
            self.destination_ids_by_source,
            self.uids_by_source
        )

        # arrange operations into an order that satisfies dependencies
        operation_order = []
        for operation in self.resolutions.values():
            if operation:
                self._add_to_operation_order(operation, operation_order)

        # run operations in order
        with transaction.atomic():
            for operation in operation_order:
                operation.run(context)

    def _add_to_operation_order(self, operation, operation_order):
        if operation in operation_order:
            # already in list - no need to add
            return

        for dependency in operation.dependencies:
            # look up the resolution for this dependency (= an Operation or None)
            resolution = self.resolutions[dependency]
            if resolution is None:
                # dependency is already satisfied with no further action
                pass
            else:
                self._add_to_operation_order(resolution, operation_order)

        operation_order.append(operation)


class ImportContext:
    """
    Persistent state required when running the import; this includes mappings from the source
    site's IDs to the destination site's IDs, which will be added to as the import proceeds
    (for example, once a page is created at the destination, we add its ID mapping so that we
    can handle references to it that appear in other imported pages).
    """
    def __init__(self, destination_ids_by_source, uids_by_source):
        self.destination_ids_by_source = destination_ids_by_source
        self.uids_by_source = uids_by_source


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
        # A list of objectives that must be satisfied before we can import this page
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
                (Page, self.object_data['parent_id'], 'exists'),
            ]
        else:
            return []

    def run(self, context):
        if self.destination_parent_id is None:
            # The destination parent ID was not known at the time this operation was built,
            # but should now exist in the page ID mapping
            source_parent_id = self.object_data['parent_id']
            self.destination_parent_id = context.destination_ids_by_source[(Page, source_parent_id)]

        parent_page = Page.objects.get(id=self.destination_parent_id)

        # Create a page object and populate its attributes from field_data
        self.page = self.model()
        for k, v in self.object_data['fields'].items():
            setattr(self.page, k, v)

        # Add the page to the database as a child of parent_page
        parent_page.add_child(instance=self.page)

        # Add an IDMapping entry for the newly created page
        uid = context.uids_by_source[(Page, self.object_data['pk'])]
        IDMapping.objects.create(uid=uid, content_object=self.page)

        # Also add it to destination_ids_by_source mapping
        source_pk = self.object_data['pk']
        context.destination_ids_by_source[(Page, source_pk)] = self.page.pk


class UpdatePage(Operation):
    def __init__(self, page, object_data):
        self.page = page
        self.object_data = object_data

    def run(self, context):
        # populate page attributes from field_data
        for k, v in self.object_data['fields'].items():
            setattr(self.page, k, v)

        self.page.save()
