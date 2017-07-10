from django.apps import apps
from django.core.exceptions import ImproperlyConfigured
from django.db.models.base import ModelBase
from django_es import es_instance
from .indices import ModelIndex
import elasticsearch
import logging

system_check_errors = []


class AlreadyRegistered(Exception):
    pass


class NotRegistered(Exception):
    pass


class IndexMapping(object):
    """
    An IndexMapping object encapsulates an instance of the Django ES application.
    Models are registered with the IndexMapping using the register() method..
    """

    def __init__(self, name='django_es'):
        self._registry = {}  # model_class class -> model_index_class instance
        self.name = name

    def get_index(self, index, indice):
        if index is None:  # get last indexex
            index = indice.indexes[-1:]
        else:  # append it
            indice.indexes.append(index)

        return index

    def register(self, model_or_iterable=None, model_index_class=None, index=None):
        """
        Registers the given model(s) with the given model_index_class class.

        The model(s) should be Model classes, not instances.

        If an model_index_class class isn't given, it will use ModelIndex (the default
        indices). If keyword arguments are given -- e.g., list_display --
        they'll be applied as options to the model_index_class class.

        If a model is already registered, this will raise AlreadyRegistered.

        If a model is abstract, this will raise ImproperlyConfigured.
        """
        if not model_index_class:
            model_index_class = ModelIndex

        if isinstance(model_or_iterable, ModelBase):
            model_or_iterable = [model_or_iterable]
        for model in model_or_iterable:
            if model._meta.abstract:
                raise ImproperlyConfigured('The model %s is abstract, so it '
                                           'cannot be registered with admin.' % model.__name__)

            if self.is_registered(model):
                raise AlreadyRegistered('The model %s is already registered' % model.__name__)

            # Ignore the registration if the model has been
            # swapped out.
            if not model._meta.swapped:
                try:
                    # create mapping for model related to a doctype
                    indice = model_index_class(model)
                    index = self.get_index(index, indice)
                    es_instance.indices.create(index=index, body={
                        'mappings': indice.mapping.to_dict(),
                        'settings': {'analysis': indice.mapping._collect_analysis()}}, ignore=400)
                except elasticsearch.exceptions.RequestError as exc:
                    raise Exception(
                        'You\'ve tried to update an existing mapping with same fields name, please visit' +
                        ' https://www.elastic.co/blog/changing-mapping-with-zero-downtime for more information.' +
                        ' Exception: ' + exc.info['error']['reason']
                    )
                except elasticsearch.exceptions.ConnectionError as exc:
                    logging.error('Cannot connect to elasticsearch instance, please verify your settings')
                    # register a model with its indice
                    self._registry[model] = indice
                else:
                    # register a model with its indice
                    self._registry[model] = indice

        # classic mapping
        if not model_or_iterable:
            # TODO : check doctype does not already exist?
            try:
                indice = model_index_class()
                index = self.get_index(index, indice)
                es_instance.indices.create(index=index, body={
                    'mappings': indice.mapping.to_dict(),
                    'settings': {
                        'analysis': indice.mapping._collect_analysis()}},
                                       ignore=400)
            except elasticsearch.exceptions.RequestError as exc:
                    raise Exception(
                        'You\'ve tried to update an existing mapping with same fields name, please visit' +
                        ' https://www.elastic.co/blog/changing-mapping-with-zero-downtime for more information.' +
                        ' Exception: ' + exc.info['error']['reason']
                    )
            except elasticsearch.exceptions.ConnectionError as exc:
                logging.error('Cannot connect to elasticsearch instance, please verify your settings')
                # register a model with its indice
                self._registry[indice.doctype] = indice
            else:
                # register a model with its indice
                self._registry[indice.doctype] = indice

    def unregister(self, model_or_iterable):
        """
        Unregisters the given model(s).

        If a model isn't already registered, this will raise NotRegistered.
        """
        if isinstance(model_or_iterable, ModelBase):
            model_or_iterable = [model_or_iterable]
        for model in model_or_iterable:
            if not self.is_registered(model):
                raise NotRegistered('The model %s is not registered' % model.__name__)
            del self._registry[model]

    def is_registered(self, model):
        """
        Check if a model class is registered with this `IndexMapping`.
        """
        return model in self._registry

    def get_index_instance(self, model):
        """
        Check if a model class is registered with this `IndexMapping`.
        """
        return self._registry[model]

    @staticmethod
    def check_dependencies():
        """
        Check that all things needed to run the admin have been correctly installed.

        The default implementation checks that admin and contenttypes apps are
        installed, as well as the auth context processor.
        """
        if not apps.is_installed('django_es'):
            raise ImproperlyConfigured(
                "Put 'django_es' in your INSTALLED_APPS "
                "setting in order to use the django_es application.")


mapping = IndexMapping()
