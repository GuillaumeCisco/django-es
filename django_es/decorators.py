from .indices import ModelIndex
from .mappings import mapping, IndexMapping


def register(*models, **kwargs):
    """
    Registers the given model(s) classes and wrapped ModelIndex class with
    django ES mapping:

    @register(Author)
    class AuthorMapping(django_es.ModelIndex):
        pass

    A kwarg of `mapping` can be passed as the django_es mapping, otherwise the default
    django_es mapping will be used.
    """

    def _model_index_wrapper(model_index_class):
        _mapping = kwargs.pop('mapping', mapping)

        if not isinstance(_mapping, IndexMapping):
            raise ValueError('mapping must subclass IndexMapping')

        if not issubclass(model_index_class, ModelIndex):
            raise ValueError('Wrapped class must subclass ModelIndex.')

        _mapping.register(models, model_index_class=model_index_class)

        return model_index_class
    return _model_index_wrapper
