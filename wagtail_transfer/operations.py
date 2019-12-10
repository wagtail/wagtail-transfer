import json
import pathlib
from urllib.parse import urlparse

from django.contrib.contenttypes.fields import GenericRelation
from django.contrib.contenttypes.models import ContentType
from django.db import models, transaction
from django.core.exceptions import ImproperlyConfigured
from django.core.files.base import ContentFile
from django.utils.functional import cached_property
from modelcluster.fields import ParentalManyToManyField
from modelcluster.models import ClusterableModel, get_all_child_relations
import requests
from treebeard.mp_tree import MP_Node
from taggit.managers import TaggableManager
from wagtail.core.fields import RichTextField, StreamField
from wagtail.core.models import Page

from .files import get_file_hash
from .richtext import get_reference_handler
from .models import get_base_model, get_base_model_for_path, get_model_for_path, IDMapping, ImportedFile


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
            raise FileTransferError  # TODO

        return ImportedFile.objects.create(
            file=ContentFile(response.content, name=self.local_filename),
            source_url=self.source_url,
            hash=self.hash,
            size=self.size,
        )

    def __hash__(self):
        return hash((self.local_filename, self.size, self.hash, self.source_url))

from .streamfield import get_object_references, update_object_ids


class ImportPlanner:
    def __init__(self, root_page_source_pk, destination_parent_id):

        self.root_page_source_pk = int(root_page_source_pk)
        if destination_parent_id is None:
            self.destination_parent_id = None
        else:
            self.destination_parent_id = int(destination_parent_id)

        # A mapping of objects on the source site to their IDs on the destination site.
        # Keys are tuples of (model_class, source_id); values are destination IDs.
        # model_class must be the highest concrete model in the inheritance tree - i.e.
        # Page, not BlogPage
        self.destination_ids_by_source = {}

        # An objective describes a state that we want to reach, e.g.
        # "page 123 must exist at the destination in its most up-to-date form". This is represented
        # as a tuple of (objective_type, model_class, source_id), where objective_type is one of:
        # 'exists': achieved when the object exists at the destination site and is listed in
        #           destination_ids_by_source
        # 'updated': achieved when the object exists at the destination site, with any data updates
        #            from the source site applied, and is listed in destination_ids_by_source
        # 'located': achieved when the object has been confirmed to exist at the destination and
        #            listed in destination_ids_by_source, OR confirmed not to exist at the
        #            destination
        # 'file-transferred' achieved when the file has been copied into storage on the destination
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

        # set of operations to be performed in this import.
        # An operation is an object with a `run` method which accomplishes the task.
        # It also has a list of dependencies - objectives that must be completed before the `run`
        # method can be called.
        self.operations = set()

        # Mapping from objectives to operations that satisfy that objective. If the objective
        # does not require any action (e.g. it's an 'ensure exists' on an object that already
        # exists), the value is None.
        # A task can be converted into an operation once all the object data relating to it has
        # been fetched.
        self.resolutions = {}

        # Mapping from tasks to operations that perform the task
        self.task_resolutions = {}

        # Mapping of source_urls to instances of ImportedFile
        self.imported_files_by_source_url = {}

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
            model = get_base_model_for_path(model_path)
            self.uids_by_source[(model, source_id)] = uid

        # add object data to the object_data_by_source dict
        for obj_data in data['objects']:
            self._add_object_data_to_lookup(obj_data)

        # retry tasks that were previously postponed due to missing object data
        self._retry_tasks()

        # for each ID in the import list, add an objective to specify that we want an up-to-date
        # copy of that object on the destination site
        for model_path, source_id in data['ids_for_import']:
            model = get_base_model_for_path(model_path)
            objective = ('updated', model, source_id)

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
        # TODO Refactor this so it looks nicer
        if objective[0] == 'file-transferred':
            self._handle_task(objective, ('transfer-file', objective[1]))
            return

        objective_type, model, source_id = objective

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
            self.destination_ids_by_source[(model, source_id)] = mapping.content_object.pk

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
                task = ('create', model, source_id)

        elif objective_type == 'updated':
            if mapping:
                # object exists locally, but we need to update it
                task = ('update', model, source_id)
            else:
                # object does not exist locally; need to create it
                task = ('create', model, source_id)

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

        if task[0] == 'transfer-file':
            operation = TransferFile(task[1])
        else:
            action, model, source_id = task
            try:
                object_data = self.object_data_by_source[(model, source_id)]
            except KeyError:
                # need to postpone this until we have the object data
                self.postponed_tasks.add((objective, task))
                self.missing_object_data.add((model, source_id))
                return

            # retrieve the specific model for this object
            specific_model = get_model_for_path(object_data['model'])

            if issubclass(specific_model, MP_Node):
                if object_data['parent_id'] is None:
                    # This is the root node; populate destination_ids_by_source so that we use the
                    # existing root node for any references to it, rather than creating a new one
                    destination_id = specific_model.get_first_root_node().pk
                    self.destination_ids_by_source[(model, source_id)] = destination_id

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
                    destination_id = self.destination_ids_by_source[(model, source_id)]
                    obj = specific_model.objects.get(pk=destination_id)
                    operation = UpdateModel(obj, object_data)
            else:
                # non-tree model
                if action == 'create':
                    operation = CreateModel(specific_model, object_data)
                else:  # action == 'update'
                    destination_id = self.destination_ids_by_source[(model, source_id)]
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
                        # their most up-to-date versions, so set the objective type to 'updated'
                        self._add_objective(('updated', related_base_model, child_obj_data['pk']))

                        # look up the child object's UID
                        uid = self.uids_by_source[(related_base_model, child_obj_data['pk'])]
                        child_uids.add(uid)

                    if action == 'update':
                        # delete any child objects on the existing object if they can't be mapped back
                        # to one of the uids in the new set
                        matched_destination_ids = IDMapping.objects.filter(
                            uid__in=child_uids,
                            content_type=ContentType.objects.get_for_model(related_base_model)
                        ).values_list('local_id', flat=True)
                        for child in getattr(obj, rel.name).all():
                            if str(child.pk) not in matched_destination_ids:
                                self.operations.add(DeleteModel(child))

        if operation is not None:
            self.operations.add(operation)

        self.resolutions[objective] = operation
        self.task_resolutions[task] = operation

        if operation is not None:
            for objective in operation.dependencies:
                self._add_objective(objective)

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
            self.uids_by_source,
            self.imported_files_by_source_url,
        )

        # arrange operations into an order that satisfies dependencies
        operation_order = []
        for operation in self.operations:
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
    def __init__(self, destination_ids_by_source, uids_by_source, imported_files_by_source_url):
        self.destination_ids_by_source = destination_ids_by_source
        self.uids_by_source = uids_by_source
        self.imported_files_by_source_url = imported_files_by_source_url


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

    @property
    def dependencies(self):
        """A list of objectives that must be satisfied before we can import this page."""
        return []


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
        reference_handler = get_reference_handler()
        for field in self.model._meta.get_fields():
            if not isinstance(field, models.Field):
                # populate data for actual fields only; ignore reverse relations
                continue

            try:
                value = self.object_data['fields'][field.name]
            except KeyError:
                continue

            # translate rich text references to their new IDs if possible
            if isinstance(field, RichTextField):
                value = reference_handler.update_ids(value, context.destination_ids_by_source)

            # translate foreignkey references to their new IDs
            if isinstance(field, models.ForeignKey):
                target_model = get_base_model(field.related_model)
                value = context.destination_ids_by_source.get((target_model, value))

            if isinstance(field, models.FileField):
                value = context.imported_files_by_source_url.get(value['download_url']).file.name
                getattr(self.instance, field.get_attname()).name = value
                continue

            if isinstance(field, TaggableManager):
                # TODO
                continue

            if isinstance(field, GenericRelation):
                # TODO
                continue

            elif isinstance(field, StreamField):
                value = json.dumps(update_object_ids(field.stream_block, json.loads(value), context.destination_ids_by_source))

            elif isinstance(field, models.ManyToManyField):
                # setting forward ManyToMany directly is prohibited
                continue

            setattr(self.instance, field.get_attname(), value)

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
                value = [context.destination_ids_by_source[(target_model, pk)] for pk in value]
                getattr(self.instance, field.get_attname()).set(value)
                save_needed = True
        if save_needed:
            # _save() for creating a page may attempt to re-add it as a child, so the instance (assumed to be already
            # in the tree) is saved directly
            self.instance.save()

    def _save(self, context):
        self.instance.save()

    @cached_property
    def dependencies(self):
        # A list of objectives that must be satisfied before we can import this page
        deps = super().dependencies

        for field in self.model._meta.get_fields():
            if isinstance(field, models.ForeignKey):
                val = self.object_data['fields'].get(field.name)
                if val is not None:
                    # TODO: consult config to decide whether objective type should be 'exists' or 'updated'
                    deps.append(
                        ('updated', get_base_model(field.related_model), val)
                    )
            elif isinstance(field, RichTextField):
                objects = get_reference_handler().get_objects(self.object_data['fields'].get(field.name))
                for model, id in objects:
                    # TODO: add config check here
                    deps.append(
                        ('exists', model, id)
                    )

            elif isinstance(field, StreamField):
                for model, id in get_object_references(field.stream_block, json.loads(self.object_data['fields'].get(field.name))):
                    # TODO: add config check here
                    deps.append(
                        ('exists', model, id)
                    )

            elif isinstance(field, models.FileField):
                value = self.object_data['fields'].get(field.name)
                existing_file = field.value_from_object(self.instance)

                if existing_file:
                    existing_file_hash = get_file_hash(field, self.instance)
                    if existing_file_hash == value['hash']:
                        # File not changed, so don't bother updating it
                        continue

                # Get the local filename
                name = pathlib.PurePosixPath(urlparse(value['download_url']).path).name
                local_filename = field.upload_to(self.instance, name)

                deps.append(('file-transferred', File(local_filename, value['size'], value['hash'], value['download_url'])))

            elif isinstance(field, models.ManyToManyField):
                model = get_base_model(field.related_model)
                for id in self.object_data['fields'].get(field.name):
                    # TODO: add config check here
                    deps.append(
                        ('exists', model, id)
                    )

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

        # Add an IDMapping entry for the newly created page
        uid = context.uids_by_source[(self.base_model, self.object_data['pk'])]
        IDMapping.objects.create(uid=uid, content_object=self.instance)

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
            deps.append(
                ('exists', get_base_model(self.model), self.object_data['parent_id']),
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


class UpdateModel(SaveOperationMixin, Operation):
    def __init__(self, instance, object_data):
        self.instance = instance
        self.model = type(instance)
        self.object_data = object_data

    def run(self, context):
        self._populate_fields(context)
        self._save(context)


class DeleteModel(Operation):
    def __init__(self, instance):
        self.instance = instance

    def run(self, context):
        self.instance.delete()

    # TODO: work out whether we need to check for incoming FK relations with on_delete=CASCADE
    # and declare those as 'must delete this first' dependencies


class TransferFile(Operation):
    def __init__(self, file):
        self.file = file

    def run(self, context):
        context.imported_files_by_source_url[self.file.source_url] = self.file.transfer()
