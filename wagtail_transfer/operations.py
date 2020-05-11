import json

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.db import models, transaction
from modelcluster.models import ClusterableModel, get_all_child_relations
from treebeard.mp_tree import MP_Node
from wagtail.core.models import Page

from .field_adapters import get_field_adapter
from .locators import get_locator_for_model
from .models import get_base_model, get_base_model_for_path, get_model_for_path

from django.utils.functional import cached_property

# Models which should be updated to their latest version when encountered in object references
default_update_related_models = ['wagtailimages.image']

UPDATE_RELATED_MODELS = [
    model_label.lower()
    for model_label in getattr(settings, 'WAGTAILTRANSFER_UPDATE_RELATED_MODELS', default_update_related_models)
]


# Models which should NOT be created in response to being encountered in object references
default_no_follow_models = ['wagtailcore.page']

NO_FOLLOW_MODELS = [
    model_label.lower()
    for model_label in getattr(settings, 'WAGTAILTRANSFER_NO_FOLLOW_MODELS', default_no_follow_models)
]


class Objective:
    """
    An objective identifies an individual database object that we want to exist on the destination
    site as a result of this import. If must_update is true, it should additionally be updated to
    the latest version that exists on the source site.
    """

    def __init__(self, model, source_id, context, must_update=False):
        self.model = model
        self.source_id = source_id
        self.context = context
        self.must_update = must_update

        # Whether this object exists at the destination; None indicates 'not checked yet'
        self._exists_at_destination = None
        self._destination_id = None

    def _find_at_destination(self):
        """
        Check if this object exists at the destination and populate self._exists_at_destination,
        self._destination_id and self.context.destination_ids_by_source accordingly
        """
        # see if there's already an entry in destination_ids_by_source
        try:
            self._destination_id = self.context.destination_ids_by_source[(self.model, self.source_id)]
            self._exists_at_destination = True
            return
        except KeyError:
            pass

        # look up uid for this item;
        # the export API is expected to supply the id->uid mapping for all referenced objects,
        # so this lookup should always succeed (and if it doesn't, we leave the KeyError uncaught)
        uid = self.context.uids_by_source[(self.model, self.source_id)]

        destination_object = get_locator_for_model(self.model).find(uid)
        if destination_object is None:
            self._exists_at_destination = False
        else:
            self._destination_id = destination_object.pk
            self._exists_at_destination = True
            self.context.destination_ids_by_source[(self.model, self.source_id)] = self._destination_id

    @property
    def exists_at_destination(self):
        if self._exists_at_destination is None:
            self._find_at_destination()

        return self._exists_at_destination

    def __eq__(self, other):
        return (
            isinstance(other, Objective)
            and (self.model, self.source_id, self.must_update) == (other.model, other.source_id, other.must_update)
        )

    def __hash__(self):
        return hash((self.model, self.source_id, self.must_update))


class ImportContext:
    """
    Persistent state required when running the import; this includes mappings from the source
    site's IDs to the destination site's IDs, which will be added to as the import proceeds
    (for example, once a page is created at the destination, we add its ID mapping so that we
    can handle references to it that appear in other imported pages).
    """
    def __init__(self):
        # A mapping of objects on the source site to their IDs on the destination site.
        # Keys are tuples of (model_class, source_id); values are destination IDs.
        # model_class must be the highest concrete model in the inheritance tree - i.e.
        # Page, not BlogPage
        self.destination_ids_by_source = {}

        # a mapping of objects on the source site to their UIDs.
        # Keys are tuples of (model_class, source_id); values are UIDs.
        self.uids_by_source = {}

        # Mapping of source_urls to instances of ImportedFile
        self.imported_files_by_source_url = {}


class ImportPlanner:
    def __init__(self, root_page_source_pk=None, destination_parent_id=None, model=None):

        if root_page_source_pk or destination_parent_id:
            self.import_type = 'page'
            self.root_page_source_pk = int(root_page_source_pk)
            if destination_parent_id is None:
                self.destination_parent_id = None
            else:
                self.destination_parent_id = int(destination_parent_id)
        elif model:
            self.import_type = 'model'
            self.model = model
        else:
            raise NotImplementedError("Missing page kwargs or specified model kwarg")

        self.context = ImportContext()

        self.objectives = set()

        # objectives that have not yet been converted into tasks
        self.unhandled_objectives = set()

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
        # objects which we have already requested and not got back, so they must be missing on the
        # source too
        self.really_missing_object_data = set()

        # set of operations to be performed in this import.
        # An operation is an object with a `run` method which accomplishes the task.
        # It also has a list of dependencies - source IDs of objects that must exist at the
        # destination before the `run` method can be called.
        self.operations = set()

        # Mapping from (model, source_id) to an operation that creates that object. If the object
        # already exists at the destination, the value is None. This will be used to solve
        # dependencies between operations, where a database record cannot be created/updated until
        # an object that it references exists at the destination site
        self.resolutions = {}

        # Mapping from tasks to operations that perform the task. This will be used to identify
        # cases where the same task arises multiple times over the course of planning the import,
        # and prevent us from running the same database operation multiple times as a result
        self.task_resolutions = {}

        # Set of (model, source_id) tuples for items that have been explicitly selected for import
        # (i.e. named in the 'ids_for_import' section of the API response), as opposed to pulled in
        # through related object references
        self.base_import_ids = set()

        # Set of (model, source_id) tuples for items that we failed to create, either because
        # NO_FOLLOW_MODELS told us not to, or because they did not exist on the source site.
        self.failed_creations = set()

    @classmethod
    def for_page(cls, source, destination):
        return cls(root_page_source_pk=source, destination_parent_id=destination)

    @classmethod
    def for_model(cls, model):
        return cls(model=model)

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
        for model_path, source_id, jsonish_uid in data['mappings']:
            model = get_base_model_for_path(model_path)
            uid = get_locator_for_model(model).uid_from_json(jsonish_uid)
            self.context.uids_by_source[(model, source_id)] = uid

        # add object data to the object_data_by_source dict
        for obj_data in data['objects']:
            self._add_object_data_to_lookup(obj_data)

        # retry tasks that were previously postponed due to missing object data
        self._retry_tasks()

        # for each ID in the import list, add to base_import_ids as an object explicitly selected
        # for import, and add an objective to specify that we want an up-to-date copy of that
        # object on the destination site
        for model_path, source_id in data['ids_for_import']:
            model = get_base_model_for_path(model_path)
            self.base_import_ids.add((model, source_id))
            objective = Objective(model, source_id, self.context, must_update=True)

            # add to the set of objectives that need handling
            self._add_objective(objective)

        # Process all unhandled objectives - which may trigger new objectives as dependencies of
        # the resulting operations - until no unhandled objectives remain
        while self.unhandled_objectives:
            objective = self.unhandled_objectives.pop()
            self._handle_objective(objective)

    def _add_object_data_to_lookup(self, obj_data):
        model = get_base_model_for_path(obj_data['model'])
        source_id = obj_data['pk']
        self.object_data_by_source[(model, source_id)] = obj_data

    def _add_objective(self, objective):
        # add to the set of objectives that need handling, unless it's one we've already seen
        # (in which case it's either in the queue to be handled, or has been handled already)
        if objective not in self.objectives:
            self.objectives.add(objective)
            self.unhandled_objectives.add(objective)

    def _handle_objective(self, objective):
        if not objective.exists_at_destination:

            # object does not exist locally - create it if we're allowed to do so, i.e.
            # it is in the set of objects explicitly selected for import, or it is a related object
            # that we have not been blocked from following by NO_FOLLOW_MODELS
            if (
                objective.model._meta.label_lower in NO_FOLLOW_MODELS
                and (objective.model, objective.source_id) not in self.base_import_ids
            ):
                # NO_FOLLOW_MODELS prevents us from creating this object
                self.failed_creations.add((objective.model, objective.source_id))
            else:
                task = ('create', objective.model, objective.source_id)
                self._handle_task(task)

        else:
            # object already exists at the destination, so any objects referencing it can go ahead
            # without being blocked by this task
            self.resolutions[(objective.model, objective.source_id)] = None

            if objective.must_update:
                task = ('update', objective.model, objective.source_id)
                self._handle_task(task)

    def _handle_task(self, task):
        """
        Attempt to convert a task into a corresponding operation.May fail if we do not yet have
        the object data for this object, in which case it will be added to postponed_tasks
        """

        # It's possible that over the course of planning the import, we will encounter multiple
        # tasks relating to the same object. For example, a page may be part of the selected
        # subtree to be imported, and, separately, be referenced from another page - both of
        # these will trigger an 'update' or 'create' task for that page (according to whether
        # it already exists or not).

        # Given that the only defined task types are 'update' and 'create', and the choice between
        # these depends ONLY on whether the object previously existed at the destination or not,
        # we can be confident that all of the tasks we encounter for a given object will be the
        # same type.

        # Therefore, if we find an existing entry for this task in task_resolutions, we know that
        # we've already handled this task and updated the ImportPlanner state accordingly
        # (including `task_resolutions`, `resolutions` and `operations`), and should quit now
        # rather than create duplicate database operations.
        if task in self.task_resolutions:
            return

        action, model, source_id = task
        try:
            object_data = self.object_data_by_source[(model, source_id)]
        except KeyError:
            # Cannot complete this task during this pass; request the missing object data,
            # unless we've already tried that
            if (model, source_id) in self.really_missing_object_data:
                # object data apparently doesn't exist on the source site either, so give up on
                # this object entirely
                if action == 'create':
                    self.failed_creations.add((model, source_id))

            else:
                # need to postpone this until we have the object data
                self.postponed_tasks.add(task)
                self.missing_object_data.add((model, source_id))

            return

        # retrieve the specific model for this object
        specific_model = get_model_for_path(object_data['model'])

        if issubclass(specific_model, MP_Node):
            if object_data['parent_id'] is None:
                # This is the root node; populate destination_ids_by_source so that we use the
                # existing root node for any references to it, rather than creating a new one
                destination_id = specific_model.get_first_root_node().pk
                self.context.destination_ids_by_source[(model, source_id)] = destination_id

                # No operation to be performed for this task
                operation = None
            elif action == 'create':
                if issubclass(specific_model, Page) and source_id == self.root_page_source_pk:
                    # this is the root page of the import; ignore the parent ID in the source
                    # record and import at the requested destination instead
                    operation = CreateTreeModel(specific_model, object_data, self.destination_parent_id)
                else:
                    operation = CreateTreeModel(specific_model, object_data)
            else:  # action == 'update'
                destination_id = self.context.destination_ids_by_source[(model, source_id)]
                obj = specific_model.objects.get(pk=destination_id)
                operation = UpdateModel(obj, object_data)
        else:
            # non-tree model
            if action == 'create':
                operation = CreateModel(specific_model, object_data)
            else:  # action == 'update'
                destination_id = self.context.destination_ids_by_source[(model, source_id)]
                obj = specific_model.objects.get(pk=destination_id)
                operation = UpdateModel(obj, object_data)

        if issubclass(specific_model, ClusterableModel):
            # Process child object relations for this item
            # and add objectives to ensure that they're all updated to their newest versions
            for rel in get_all_child_relations(specific_model):
                related_base_model = get_base_model(rel.related_model)
                child_uids = set()

                for child_obj_data in object_data['fields'][rel.name]:
                    # Add child object data to the object_data_by_source lookup
                    self._add_object_data_to_lookup(child_obj_data)

                    # Add an objective for handling the child object. Regardless of whether
                    # this is a 'create' or 'update' task, we want the child objects to be at
                    # their most up-to-date versions, so set the objective to 'must update'
                    self._add_objective(
                        Objective(related_base_model, child_obj_data['pk'], self.context, must_update=True)
                    )

                    # look up the child object's UID
                    uid = self.context.uids_by_source[(related_base_model, child_obj_data['pk'])]
                    child_uids.add(uid)

                if action == 'update':
                    # delete any child objects on the existing object if they can't be mapped back
                    # to one of the uids in the new set
                    locator = get_locator_for_model(related_base_model)
                    matched_destination_ids = set()
                    for uid in child_uids:
                        child = locator.find(uid)
                        if child is not None:
                            matched_destination_ids.add(child.pk)

                    for child in getattr(obj, rel.name).all():
                        if child.pk not in matched_destination_ids:
                            self.operations.add(DeleteModel(child))

        if operation is not None:
            self.operations.add(operation)

        if action == 'create':
            # For 'create' actions, record this operation in `resolutions`, so that any operations
            # that identify this object as a dependency know that this operation has to happen
            # first.

            # (Alternatively, the operation can be None, and that's fine too: it means that we've
            # been able to populate destination_ids_by_source with no further action, and so the
            # dependent operation has nothing to wait for.)

            # For 'update' actions, this doesn't matter, since we can happily fill in the
            # destination ID wherever it's being referenced, regardless of whether that object has
            # completed its update or not; in this case, we would have already set the resolution
            # to None during _handle_objective.
            self.resolutions[(model, source_id)] = operation

        self.task_resolutions[task] = operation

        if operation is not None:
            for model, source_id, is_hard_dep in operation.dependencies:
                self._add_objective(
                    Objective(model, source_id, self.context, must_update=(model._meta.label_lower in UPDATE_RELATED_MODELS))
                )

    def _retry_tasks(self):
        """
        Retry tasks that were previously postponed due to missing object data
        """
        previous_postponed_tasks = self.postponed_tasks
        self.postponed_tasks = set()

        for key in self.missing_object_data:
            # The latest JSON packet should have populated object_data_by_source with any
            # previously missing objects, if they exist at the source at all - so any that are
            # still missing must also be missing at the source
            if key not in self.object_data_by_source:
                self.really_missing_object_data.add(key)

        self.missing_object_data.clear()

        for task in previous_postponed_tasks:
            self._handle_task(task)

    def run(self):
        if self.unhandled_objectives or self.postponed_tasks:
            raise ImproperlyConfigured("Cannot run import until all dependencies are resoved")

        # filter out unsatisfiable operations
        statuses = {}
        satisfiable_operations = [
            op for op in self.operations
            if self._check_satisfiable(op, statuses)
        ]

        # arrange operations into an order that satisfies dependencies
        operation_order = []
        for operation in satisfiable_operations:
            self._add_to_operation_order(operation, operation_order, [operation])

        # run operations in order
        with transaction.atomic():
            for operation in operation_order:
                operation.run(self.context)

    def _check_satisfiable(self, operation, statuses):
        # Check whether the given operation's dependencies are satisfiable. statuses is a dict of
        # previous results - keys are (model, id) pairs and the value is:
        #  True - dependency is satisfiable
        #  False - dependency is not satisfiable
        #  None - the satisfiability check is currently in progress -
        #         if we encounter this we have found a circular dependency.
        for (model, id, is_hard_dep) in operation.dependencies:
            if not is_hard_dep:
                continue  # ignore soft dependencies here

            try:
                # Look for a previous result for this dependency
                result = statuses[(model, id)]
                if result is False or result is None:
                    # Dependency is known to be unsatisfiable, or we have just found a circular
                    # dependency
                    return False
            except KeyError:
                # No previous result - need to determine it now.
                # Mark this as 'in progress', to spot circular dependencies
                statuses[(model, id)] = None

                # Look for a resolution for this dependency (i.e. an Operation that creates it)
                try:
                    resolution = self.resolutions[(model, id)]
                except KeyError:
                    # If the resolution is missing, it *should* be for one of the reasons we've
                    # accounted for and logged in failed_creations. Otherwise, that's a bug, and
                    # we should fail loudly now
                    if (model, id) not in self.failed_creations:
                        raise

                    # The dependency is not satisfiable (for a reason we know about in
                    # failed_creations), and so the overall operation fails too
                    statuses[(model, id)] = False
                    return False

                if resolution is None:
                    # the dependency was already satisfied, with no further action required
                    statuses[(model, id)] = True
                else:
                    # resolution is an Operation that we now need to check recursively
                    result = self._check_satisfiable(resolution, statuses)
                    statuses[(model, id)] = result
                    if result is False:
                        return False

        # We've got through all the dependencies without anything failing. Yay!
        return True

    def _add_to_operation_order(self, operation, operation_order, path):
        # path is the sequence of dependencies we've followed so far, starting from the top-level
        # operation picked from satisfiable_operations in `run`, to find one we can add

        if operation in operation_order:
            # already in list - no need to add
            return

        for dep_model, dep_source_id, dep_is_hard in operation.dependencies:
            # look up the resolution for this dependency (= an Operation or None)
            try:
                resolution = self.resolutions[(dep_model, dep_source_id)]
            except KeyError:
                # At this point this should only happen for soft dependencies, as we should have
                # stripped out unsatisfiable hard dependencies via _check_satisfiable
                assert not dep_is_hard

                # So, given that this is a soft dependency, carry on regardless
                continue

            if resolution is None:
                # dependency is already satisfied with no further action
                continue
            elif resolution in path:
                # we have a circular dependency; we have to break it somewhere, so break it here
                continue
            else:
                self._add_to_operation_order(resolution, operation_order, path + [resolution])

        operation_order.append(operation)


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
        raise NotImplementedError

    @property
    def dependencies(self):
        """
        A set of (model, source_id, is_hard) tuples that should exist at the destination before we
        can import this page.
        is_hard is a boolean - if True, then the object MUST exist in order for this operation to
            succeed; if False, then the operation can still complete without it (albeit possibly
            with broken links).
        """
        return set()


class SaveOperationMixin:
    """
    Mixin class to handle the common logic of CreateModel and UpdateModel operations, namely:
    * Writing the field data stored in `self.object_data` to the model instance `self.instance` -
      which may be an existing instance (in the case of an update) or a new unsaved one (in the
      case of a creation)
    * Remapping any IDs of related ids that appear in this field data
    * Declaring these related objects as dependencies

    Requires subclasses to define `self.model`, `self.instance` and `self.object_data`.
    """
    @cached_property
    def base_model(self):
        return get_base_model(self.model)

    def _populate_fields(self, context):
        for field in self.model._meta.get_fields():
            if not isinstance(field, models.Field):
                # populate data for actual fields only; ignore reverse relations
                continue

            try:
                value = self.object_data['fields'][field.name]
            except KeyError:
                continue

            get_field_adapter(field).populate_field(self.instance, value, context)

    def _populate_many_to_many_fields(self, context):
        save_needed = False

        # for ManyToManyField, this must be done after saving so that the instance has an id.
        # for ParentalManyToManyField, this could be done before, but doing both together avoids additional
        # complexity as the method is identical
        for field in self.model._meta.get_fields():
            if isinstance(field, models.ManyToManyField):
                try:
                    value = self.object_data['fields'][field.name]
                except KeyError:
                    continue
                target_model = get_base_model(field.related_model)

                # translate list of source site ids to destination site ids
                new_value = []
                for pk in value:
                    try:
                        new_pk = context.destination_ids_by_source[(target_model, pk)]
                    except KeyError:
                        continue
                    new_value.append(new_pk)

                getattr(self.instance, field.get_attname()).set(new_value)
                save_needed = True
        if save_needed:
            # _save() for creating a page may attempt to re-add it as a child, so the instance (assumed to be already
            # in the tree) is saved directly
            self.instance.save()

    def _save(self, context):
        self.instance.save()

    @cached_property
    def dependencies(self):
        # the set of objects that must be created before we can import this object
        deps = super().dependencies

        for field in self.model._meta.get_fields():
            if isinstance(field, models.Field):
                val = self.object_data['fields'].get(field.name)
                deps.update(get_field_adapter(field).get_dependencies(val))

        return deps


class CreateModel(SaveOperationMixin, Operation):
    def __init__(self, model, object_data):
        self.model = model
        self.object_data = object_data
        self.instance = self.model()

    def run(self, context):
        # Create object and populate its attributes from field_data
        self._populate_fields(context)
        self._save(context)
        self._populate_many_to_many_fields(context)

        # record the UID for the newly created page
        uid = context.uids_by_source[(self.base_model, self.object_data['pk'])]
        get_locator_for_model(self.base_model).attach_uid(self.instance, uid)

        # Also add it to destination_ids_by_source mapping
        source_pk = self.object_data['pk']
        context.destination_ids_by_source[(self.base_model, source_pk)] = self.instance.pk


class CreateTreeModel(CreateModel):
    """
    Create an instance of a model that is structured in a Treebeard tree

    For example: Pages and Collections
    """
    def __init__(self, model, object_data, destination_parent_id=None):
        super().__init__(model, object_data)
        self.destination_parent_id = destination_parent_id

    @cached_property
    def dependencies(self):
        deps = super().dependencies
        if self.destination_parent_id is None:
            # need to ensure parent page is imported before this one
            deps.add(
                (get_base_model(self.model), self.object_data['parent_id'], True),
            )

        return deps

    def _save(self, context):
        if self.destination_parent_id is None:
            # The destination parent ID was not known at the time this operation was built,
            # but should now exist in the page ID mapping
            source_parent_id = self.object_data['parent_id']
            self.destination_parent_id = context.destination_ids_by_source[(get_base_model(self.model), source_parent_id)]

        parent = get_base_model(self.model).objects.get(id=self.destination_parent_id)

        # Add the page to the database as a child of parent
        parent.add_child(instance=self.instance)

        if isinstance(self.instance, Page):
            # Also save this as a revision, so that it exists in revision history
            self.instance.save_revision(changed=False)


class UpdateModel(SaveOperationMixin, Operation):
    def __init__(self, instance, object_data):
        self.instance = instance
        self.model = type(instance)
        self.object_data = object_data

    def run(self, context):
        self._populate_fields(context)
        self._save(context)
        self._populate_many_to_many_fields(context)

    def _save(self, context):
        super()._save(context)
        if isinstance(self.instance, Page):
            # Also save this as a revision, so that:
            # * the edit-page view will pick up this imported version rather than any currently-existing drafts
            # * it exists in revision history
            # * the Page.draft_title field (as used in page listings in the admin) is updated to match the real title
            self.instance.save_revision(changed=False)


class DeleteModel(Operation):
    def __init__(self, instance):
        self.instance = instance

    def run(self, context):
        self.instance.delete()

    # TODO: work out whether we need to check for incoming FK relations with on_delete=CASCADE
    # and declare those as 'must delete this first' dependencies
