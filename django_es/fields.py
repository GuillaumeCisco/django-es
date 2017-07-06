from datetime import date, datetime
from dateutil import parser
from elasticsearch_dsl import Field
from elasticsearch_dsl.field import InnerObject, ValidationException
from django.template import Context, loader

__all__ = [
    'Object', 'Nested', 'Date', 'String', 'Text', 'Keyword', 'Float',
    'Byte', 'Short', 'Integer', 'Long', 'Boolean', 'Ip',
    'Attachment', 'GeoPoint', 'GeoShape', 'Completion'
]


class AbstractField(Field):
    """
    Represents an elasticsearch index field and values from given objects.
    Currently does not support binary fields, but those can be created by manually providing a dictionary.

    Values are extracted using the `_model_attr` or `_eval_as` attribute.
    """

    def __init__(self, *args, **kwargs):
        """
        Performs several checks to ensure that the provided attributes are valid. Will not check their values.
        """
        self._model_attr = kwargs.pop('_model_attr', None)
        self._eval_func = kwargs.pop('_eval_as', None)
        self._template_name = kwargs.pop('_template', None)
        super(AbstractField, self).__init__(*args, **kwargs)

    def value(self, obj):
        """
        Computes the value of this field to update the index.
        :param obj: object instance, as a dictionary or as a model instance.
        """
        if self._template_name:
            t = loader.select_template([self._template_name])
            return t.render(Context({'object': obj}))

        if self._eval_func:
            try:
                return eval(self._eval_func)
            except Exception as e:
                raise type(e)(
                    'Could not compute value of {} field (_eval_as=`{}`): {}.'.format(unicode(self), self._eval_func,
                                                                                      unicode(e)))

        elif self._model_attr:
            if isinstance(obj, dict):
                return obj[self._model_attr]
            current_obj = getattr(obj, self._model_attr)

            if callable(current_obj):
                return current_obj()
            else:
                return current_obj

        else:
            raise KeyError(
                '{0} gets its value via a model attribute, an eval function, a template, or is prepared in a method '
                'call but none of `_model_attr`, `_eval_as,` `_template,` `prepare_{0}` is provided.'.format(
                    unicode(self)))


# Redefine Elasticsearch dsl fields for our needs


class Object(InnerObject, AbstractField):
    name = 'object'


class Nested(InnerObject, AbstractField):
    name = 'nested'

    def __init__(self, *args, **kwargs):
        # change the default for Nested fields
        kwargs.setdefault('multi', True)
        super(Nested, self).__init__(*args, **kwargs)


class Date(AbstractField):
    name = 'date'
    _coerce = True

    def _deserialize(self, data):
        if not data:
            return None
        if isinstance(data, date):
            return data
        if isinstance(data, int):
            return datetime.utcfromtimestamp(data / 1000)

        try:
            # TODO: add format awareness
            return parser.parse(data)
        except Exception as e:
            raise ValidationException('Could not parse date from the value (%r)' % data, e)


class String(AbstractField):
    _param_defs = {
        'fields': {'type': 'field', 'hash': True},
        'analyzer': {'type': 'analyzer'},
        'index_analyzer': {'type': 'analyzer'},
        'search_analyzer': {'type': 'analyzer'},
    }
    name = 'string'

    def _empty(self):
        return ''


class Text(AbstractField):
    _param_defs = {
        'fields': {'type': 'field', 'hash': True},
        'analyzer': {'type': 'analyzer'},
        'search_analyzer': {'type': 'analyzer'},
        'search_quote_analyzer': {'type': 'analyzer'},
    }
    name = 'text'

    def _empty(self):
        return ''


class Keyword(AbstractField):
    _param_defs = {
        'fields': {'type': 'field', 'hash': True},
        'search_analyzer': {'type': 'analyzer'},
    }
    name = 'keyword'

    def _empty(self):
        return ''


class Boolean(AbstractField):
    name = 'boolean'

    def _deserialize(self, data):
        if data is None:
            return None
        return bool(data)

    def clean(self, data):
        if data is not None:
            data = self.deserialize(data)
        if data is None and self._required:
            raise ValidationException("Value required for this field.")
        return data


class Float(AbstractField):
    name = 'float'


class HalfFloat(AbstractField):
    name = 'half_float'


class Double(AbstractField):
    name = 'double'


class Byte(AbstractField):
    name = 'byte'


class Short(AbstractField):
    name = 'short'


class Integer(AbstractField):
    name = 'integer'


class Long(AbstractField):
    name = 'long'


class Ip(AbstractField):
    name = 'ip'


class Attachment(AbstractField):
    name = 'attachment'


class GeoPoint(AbstractField):
    name = 'geo_point'


class GeoShape(AbstractField):
    name = 'geo_shape'


class Completion(AbstractField):
    name = 'completion'


class Percolator(AbstractField):
    name = 'percolator'


# Correspondence between a Django field and an elasticsearch field.
def django_field_to_index(field, **attr):
    """
    Returns the index field type that would likely be associated with each Django type.
    """

    dj_type = field.get_internal_type()

    if dj_type in ('DateField', 'DateTimeField'):
        return Date(**attr)
    elif dj_type in ('BooleanField', 'NullBooleanField'):
        return Boolean(**attr)
    elif dj_type in ('DecimalField', 'FloatField'):
        return Float(**attr)
    elif dj_type in ('PositiveSmallIntegerField', 'SmallIntegerField'):
        return Short(**attr)
    elif dj_type in ('IntegerField', 'PositiveIntegerField', 'AutoField'):
        return Integer(**attr)
    elif dj_type in ('BigIntegerField',):
        return Long(**attr)
    elif dj_type in ('GenericIPAddressField',):
        return Ip(**attr)

    return String(**attr)
