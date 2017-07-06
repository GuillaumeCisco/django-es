import logging
from elasticsearch_dsl import Field, Mapping

from six import iteritems

from .signals import get_signal_processor
from .fields import django_field_to_index, String


class ModelIndex(object):
    """
    Introspects a model to generate an indexable mapping and methods to extract objects.
    Supports custom fields, including Python code, and all elasticsearch field types (apart from binary type).

    ModelIndex does efficient querying by only fetching from the database fields which are to be indexed.

    How to create an index?

    1. Create a class which inherits from ModelIndex.
    2. Define custom indexed fields as class attributes. Values must be instances Field. Important info in 3b.
    3. Define a `Meta` subclass, which must contain at least `model` as a class attribute.
        a. Optional class attributes: `fields`, `excludes` and `additional_fields`.
        b. If custom indexed field requires model attributes which are not in the difference between `fields` and
        `excludes`, these must be defined in `additional_fields`.
    """

    def __init__(self, model, *args):
        # Introspect the model, adding/removing fields as needed.
        # Adds/Excludes should happen only if the fields are not already
        # defined in `self.fields`.
        try:
            _meta = getattr(self, 'Meta')
        except AttributeError:
            raise AttributeError('ModelIndex {} does not contain a Meta class.'.format(self.__class__.__name__))

        self.model = model
        self.doc_type = getattr(_meta, 'doc_type', None if self.model is None else self.model.__name__.lower())

        if self.model is None and self.doc_type is None:
            raise AttributeError(
                'ModelIndex {} without Model declaration need a doc_type.'.format(self.__class__.__name__))

        self.fields = {}
        self.index = getattr(_meta, 'index', 'django_es')
        self.indexes = [self.populate_index()]
        fields = getattr(_meta, 'fields', [])
        excludes = getattr(_meta, 'exclude', [])
        hotfixes = getattr(_meta, 'hotfixes', {})
        additional_fields = getattr(_meta, 'additional_fields', [])
        self.id_field = getattr(_meta, 'id_field', 'pk')

        # Add in fields from the model.
        self.fields.update(self._get_fields(fields, excludes, hotfixes))
        self.fields_to_fetch = list(set(self.fields.keys()).union(additional_fields))

        # create the mapping instance
        self.mapping = getattr(_meta, 'mapping', Mapping(self.doc_type))

        # Adding or updating the fields which are defined at class level.
        for cls_attr, obj in iteritems(self.__class__.__dict__):
            if not isinstance(obj, Field):
                continue

            if cls_attr in self.fields:
                overwrite_info = 'Overwriting implicitly defined model field {} ({}) its explicit definition: {}.'
                logging.info(overwrite_info.format(cls_attr, unicode(self.fields[cls_attr]), unicode(obj)))

            # check if override of a model_attr field and remove it for avoiding duplication (stay in fields_to_fetch)
            if hasattr(obj, '_model_attr') and obj._model_attr in self.fields:
                del self.fields[obj._model_attr]
            self.fields[cls_attr] = obj

        for attr, value in iteritems(self.fields):
            self.mapping.field(attr, value)

        self.signal_processor = get_signal_processor()
        self.signal_processor.setup(self.model)

    def populate_index(self):
        return self.index

    @staticmethod
    def matches_indexing_condition(item):
        """
        Returns True by default to index all documents.
        """
        return True

    def get_model(self):
        return self.model

    def get_mapping(self):
        """
        :return: a dictionary which can be used to generate the elasticsearch index mapping for this doctype.
        """
        return self.mapping.to_dict()

    def serialize_object(self, obj, obj_pk=None):
        """
        Serializes an object for it to be added to the index.

        :param obj: Object to be serialized. Optional if obj_pk is passed.
        :param obj_pk: Object primary key. Supersedded by `obj` if available.
        :return: A dictionary representing the object as defined in the mapping.
        """
        if not obj:
            try:
                # We're using `filter` followed by `values` in order to only fetch the required fields.
                obj = self.model.objects.filter(pk=obj_pk).values(*self.fields_to_fetch)[0]
            except Exception as e:
                error = 'Could not find object of primary key = {} in model {} (model index class {}).' +\
                        ' (Original exception: {}.)'
                raise ValueError(error.format(obj_pk, self.model, self.__class__.__name__, e))

        serialized_object = {}

        for name, field in iteritems(self.fields):
            if hasattr(self, "prepare_%s" % name):
                value = getattr(self, "prepare_%s" % name)(obj)
            else:
                value = field.value(obj)

            serialized_object[name] = value

        return serialized_object

    def _get_fields(self, fields, excludes, hotfixes):
        """
        Given any explicit fields to include and fields to exclude, add
        additional fields based on the associated model. If the field needs a hotfix, apply it.
        """
        final_fields = {}
        fields = fields or []
        excludes = excludes or []

        for f in self.model._meta.fields:
            # If the field name is already present, skip
            if f.name in self.fields:
                continue

            # If field is not present in explicit field listing, skip
            if fields and f.name not in fields:
                continue

            # If field is in exclude list, skip
            if excludes and f.name in excludes:
                continue

            # If field is a relation, skip.
            if getattr(f, 'rel'):
                continue

            attr = {'_model_attr': f.name}
            if f.name in hotfixes:
                attr.update(hotfixes[f.name])

            final_fields[f.name] = django_field_to_index(f, **attr)

        return final_fields

    def __str__(self):
        return '<{0.__class__.__name__}:{0.model.__name__}>'.format(self)
