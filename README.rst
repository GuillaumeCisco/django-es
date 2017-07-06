Django ES
=========


.. contents:: Table of contents
   :depth: 2

Purpose
=======

Django ES is a Django wrapper for
`elasticsearch-dsl-py <https://github.com/elasticsearch/elasticsearch-dsl-py>`__.

Originally it's a fork from `bungiesearch <https://github.com/ChristopherRabotin/bungiesearch>`__ so
you'll find a lot of things in common.
The big change is it uses register admin as a philosophy instead of django manager.
So a lot of code has been removed and there is a lot of changes.
There are no alias, no management commands.

This contribution use elasticsearch 5.x and its restrictions (unique field name related to one unique mapping definition).
CRUD operations are mostly done by elasticsearch-dsl library for more control and maintainability.

Features
========

-  Django Model Mapping

   -  Very easy mapping (no lies).
   -  Automatic model mapping (and supports undefined models by
      returning a ``Result`` instance of ``elasticsearch-dsl-py``).

-  Django Admin register like
   -  Register your model as you do with Django Admin contribution
      in a separated file.

-  Django signals

   -  Connect to pre_save, post save and pre delete signals for the elasticsearch
      index to correctly reflect the database (almost) at all times.

-  Requirements

   -  Django >= 1.8
   -  Python 2.7 (**no Python 3 support yet**)


Installation
============

Install the package
-------------------

The easiest way is to install the package from github:

``pip install git+ssh://git@github.com/GuillaumeCisco/django-es.git``

**Note:** Check your version of Django after installing django-es. It
was reported to me directly that installing django-es may upgrade
your version of Django, although I haven't been able to confirm that
myself. django-es depends on Django 1.8 and above.

In Django
---------

Updating your Django models
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Create a ``djangoes.py`` python file (or package) and register your models.
More description, in examples following.

Creating Django ES search indexes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The search indexes define how Django ES should serialize each of the
model's objects. It effectively defines how your object is serialized
and how the Elasticsearch index should be structured.
Now you should run a first time your server for allowing autodiscover
module to generate mapping and communicate with your ElasticSearch
server.


In Elasticsearch
----------------

You can now open your elasticsearch dashboard, such as Elastic HQ, and
see that your index is created with the appropriate mapping and has
items that are indexed.

Quick start example
===================


Procedure
---------

Add 'django_es' to `INSTALLED_APPS`.
You can define in your own code an `ES_CLIENT` parameter for connecting to your Elasticsearch instance,
By default `ES_CLIENT` is `Elasticsearch()`

Example
-------

### Django Model

.. code:: python

    from django.db import models
    from django.core.urlresolvers import reverse
    from autoslug import AutoSlugField
    from wall.models import Wall
    from category.models import Category


    class MyModel(models.Model):

        name = models.CharField(max_length=128, null=True, blank=True)
        created = models.DateTimeField(auto_now_add=True)
        wall = models.ForeignKey(Wall, related_name='mymodels', null=True, blank=True)
        slug = AutoSlugField(populate_from='populate_slug', unique=True)
        last_modified = models.DateTimeField(auto_now_add=True)
        is_finalized = models.BooleanField(default=False)
        is_recorded = models.BooleanField(default=False)
        desc = models.CharField(max_length=4096, null=True, blank=True)
        diff_date = models.DateTimeField()
        duration = models.DurationField(null=True, blank=True)
        category = models.ForeignKey(Category)

        def __str__(self):
            return self.name

        def get_absolute_url(self):
            return reverse('video', kwargs={'slug': self.slug})

        # use this technique because name if from parent class
        def populate_slug(self):
            return self.name or 'mymodel'

        class Meta(Media.Meta):
            app_label = 'media'


ModelIndex
~~~~~~~~~~


The following ModelIndex will generate a mapping containing all fields
from ``MyModel``, minus those defined in ``MyModelModelIndex.Meta.exclude``.
When the mapping is generated, each field will the most appropriate
`elasticsearch core
type <https://www.elastic.co/guide/en/elasticsearch/reference/current/mapping-types.html>`__,
with default attributes (as defined in django_es.fields).

These default attributes can be overwritten with
``MyModelModelIndex.Meta.hotfixes``: each dictionary key must be field
defined either in the model or in the ModelIndex subclass
(``MyModelModelIndex`` in this case).

.. code:: python

    from django_es import mapping
    from django_es.fields import String, Date, Integer
    from django_es.indices import ModelIndex
    from media.models import MyModel
    from elasticsearch_dsl.analysis import Analyzer
    from utils.fields import Completion


    class MyModelModelIndex(ModelIndex):
        description = String(analyzer='snowball', _model_attr='desc')
        created_date = Date(_model_attr='created')
        category = Integer(_eval_as='obj.category.id')
        img = String()
        author = String()
        suggest = Completion(
            analyzer=Analyzer('simple'),
            search_analyzer=Analyzer('simple'),
            preserve_position_increments=False,
            preserve_separators=False,
            payloads=True,
            context={
                'type': {
                    'type': 'category',
                    'path': '_type'
                }
            }
        )

        class Meta:
            index = 'django_es'  # optional but recommended, default is `django_es`, ever use `populate_index` method
            exclude = ('last_modified', 'is_finalized', 'is_recorded', 'diff_date', 'duration',)

        def prepare_img(self, obj):
            # How we want to store this field in elasticsearch
            from media.serializers.liveVideo import MyModelSerializer
            return MyModelSerializer._img(obj, '48x48')  # getting related image passing res

        def prepare_author(self, obj):
            return obj.wall.profile.get_full_name()

        def prepare_suggest(self, obj):
            # How we want to store this field in elasticsearch
            return {
                'input': [obj.name, obj.desc, obj.wall.profile.get_full_name()],
                'output': obj.name + ' - ' + obj.wall.profile.get_full_name(),
                'payload': {
                    'slug': obj.slug,
                    'img': self.prepare_img(obj),
                    'category': obj.category.id
                }
            }

        mapping.register(MyModel, MyModelModelIndex)

The last line is important, it allows Django ES to create the mapping related to this model
and to put in on the elasticsearch server.

This `djangoes.py` file use a Completion Field not related to the model field
derived from elasticsearch-dsl.fields.
You can create your own fields if there are not already provided by elasticsearch-dsl
or this contribution.

.. code:: python

    from elasticsearch_dsl import Field

    class Completion(Field):
    _param_defs = {
            'fields': {'type': 'field', 'hash': True},
            'analyzer': {'type': 'analyzer'},
            'search_analyzer': {'type': 'analyzer'},
            'max_input_length': {'type': 'integer'}
        }
        name = 'completion'

        def _empty(self):
            return ''


Now, for your mapping and index to be generated, you need to launch your server a first time.
Your mappings can be updated following these
`elasticsearch mappings rules <https://www.elastic.co/blog/changing-mapping-with-zero-downtime>`__,

Creating/Updating, Deleting documents
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

By default, your documents are created on ``post_save`` signal of the model.
But with an API oriented website or with django forms, you can directly use
elasticsearch-dsl methods or simply use functions defined in ``utils``:
``update_index`` and ``delete_index``

Example:

.. code:: python

    # for updating/deleting one or more instances simultaneously

    update_index([instance, ...], sender, bulk_size=1)  # chose your action : index or delete, default is index


    # for deleting
    delete_index_item(instance, sender)


The ``update_index`` functions use the ``bulk``/``bulk_index`` method of elasticsearch for performing
several actions in a row.

You can create your own utils methods.


Querying your elasticsearch documents
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

You can query your documents using elasticsearch-dsl methods. It's the easier way.
Example:

.. code:: python

    from elasticsearch import Elasticsearch
    from elasticsearch_dsl import Q as _Q
    from elasticsearch_dsl import Search
    from elasticsearch_dsl.query import MultiMatch

    searchstr = 'Some terms to research'

    client = Elasticsearch()
    s = Search().using(client)
    fields = ["name^2.0", "description^1.5", "author^1.0"]
    s.query(MultiMatch(query=searchstr, type='best_fields', fields=fields, tie_breaker=0.3))
    #or
    #s.query(_Q('query_string', query=' AND '.join([x + '~2' for x in searchstr.split(' ')]), use_dis_max=True, fields=fields, tie_breaker=0.3))
    s.aggs.bucket('list', 'filter', term={'_type': 'mymodel'}) \
        .metric('obj',
                'top_hits',
                **{'_source': ['name', 'slug', 'img'],
                   'from': (int(page) - 1) * 20,
                   'size': 20
                   }
                )
    s = s[:0]  # getting only aggregations results
    response = s.execute()

    count = response.aggregations.list.obj.hits.total
    res = [x._source.to_dict() for x in response.aggregations.list.obj.hits.hits]


You also can use your ``suggest`` field defined previously:

.. code:: python

    from elasticsearch import Elasticsearch
    from elasticsearch_dsl import Search

    searchstr = 'Some terms to research'
    client = Elasticsearch()

    s = Search().using(client)\
            .suggest('lives', searchstr, completion={'field': 'suggest', 'fuzzy': True, 'size': 5, 'context': {'type': 'mymodel'}})
    s = s[:0]  # getting only suggestions results
    response = s.execute()

    def format_result(options):
        results = []
        for x in options:
            d = x['payload'].to_dict()
            d.update(name=x.text)
            results.append(d)
        return results

        lives = format_result(response.suggest.lives[0]['options'])


Django settings
~~~~~~~~~~~~~~~

You can define a ``DJANGO_ES`` dict in your settings for overriding the way signals
are dealt with models associated with Django_ES instances.
You can inspect the code and find in the signals packages inspiration for your business logic,
or use the classic ``BaseDjangoESSignalProcessor`` which will use a buffer of 100 objects before
creating/updating/deleting deleting elasticsearch doctype objects.

.. code:: python

    DJANGO_ES = {
                'SIGNAL_CLASS': 'BaseDjangoESSignalProcessor'  # default
                }

Documentation
=============

ModelIndex
----------

A ``ModelIndex`` defines mapping and object extraction for indexing of a
given Django model. It is possible to create directly a mapping without
a model too, just pass a doctype.

Any Django model to be managed by Django ES must have a defined
ModelIndex subclass. This subclass must contain a subclass called
``Meta``.

Class attributes
~~~~~~~~~~~~~~~~

As detailed below, the doc type mapping will contain fields from the
model it related to. However, one may often need to index fields which
correspond to either a concatenation of fields of the model or some
logical operation.

Django ES makes this very easy: simply define a class attribute as
whichever core type, and set to the ``eval_as`` constructor parameter to
a one line Python statement. The object is referenced as ``obj`` (not
``self`` nor ``object``, just ``obj``).

You can also use ``prepare_%s`` functions with name of the field for more complex
serialization.

Example
^^^^^^^

This is a partial example as the Meta subclass is not defined, yet
mandatory (cf. below).

.. code:: python

    from django_es.fields import Date, String, Integer
    from django_es.indices import ModelIndex

    class MyModelModelIndex(ModelIndex):
        description = String(analyzer='snowball', _model_attr='desc')
        created_date = Date(_model_attr='created')
        category = Integer(_eval_as='obj.category.id')
        img = String()

        def prepare_img(self, obj):
            # How we want to store this field in elasticsearch
            from media.serializers.liveVideo import MyModelSerializer
            return MyModelSerializer._img(obj, '48x48')

Here, ``img`` will be part of the doc
type mapping, but won't be reversed mapped since those fields do not
exist in the model.
``description`` and ``created_date`` use the ``_model_attr`` link for redefining fields name.
``category`` will be evaluated as an integer related to the Category foreignkey.

This can also be used to index foreign keys:

.. code:: python

    some_field_name = String(_eval_as='",".join([item for item in obj.some_foreign_relation.values_list("some_field", flat=True)]) if obj.some_foreign_relation else ""')

    # or

    def prepare_some_field_name(self, obj):
        if obj.some_foreign_relation:
            return ','.join([item for item in obj.some_foreign_relation.values_list("some_field", flat=True)])
        return ''

Class methods
~~~~~~~~~~~~~

populate\_index
^^^^^^^^^^^^^^^

Override this method if you want to deal with dynamic index generation.
Example with dynamic date:
It will create a new index every day.

.. code:: python

    def populate_index(self):
        return 'my_index_name-%(now)s' % {'now': now().strftime("%Y.%m.%d")}

matches\_indexing\_condition
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Override this function to specify whether an item should be indexed or
not. This is useful when defining multiple indices (and ModelIndex
classes) for a given model. This method's signature and super class code
is as follows, and allows indexing of all items.

.. code:: python

    def matches_indexing_condition(self, item):
        return True

For example, if a given elasticsearch index should contain only item
whose title starts with ``"Awesome"``, then this method can be
overridden as follows.

.. code:: python

    def matches_indexing_condition(self, item):
        return item.title.startswith("Awesome")

Meta subclass attributes
~~~~~~~~~~~~~~~~~~~~~~~~

**Note**: in the following, any variable defined as being a ``list``
could also be a ``tuple``.

fields
^^^^^^

*Optional:* list of fields (or columns) which must be fetched when
serializing the object for elasticsearch, or when reverse mapping the
object from elasticsearch back to a Django Model instance. By default,
all fields will be fetched. Setting this *will* restrict which fields
can be fetched and may lead to errors when serializing the object. It is
recommended to use the ``exclude`` attribute instead (cf. below).

exclude
^^^^^^^

*Optional:* list of fields (or columns) which must not be fetched when
serializing or deserializing the object.

hotfixes
^^^^^^^^

*Optional:* a dictionary whose keys are index fields and whose values
are dictionaries which define `core type
attributes <https://www.elastic.co/guide/en/elasticsearch/reference/current/mapping-types.html>`__.
By default, there aren't any special settings, apart for String fields,
where the
`analyzer <http://www.elasticsearch.org/guide/en/elasticsearch/reference/current/analysis-analyzers.html>`__
is set to
```snowball`` <http://www.elasticsearch.org/guide/en/elasticsearch/reference/current/analysis-snowball-analyzer.html>`__
(``{'analyzer': 'snowball'}``).

additional\_fields
^^^^^^^^^^^^^^^^^^

*Optional:* additional fields to fetch for mapping, may it be for
``eval_as``/``prepare_%s`` fields or when returning the object from the database.


id\_field
^^^^^^^^^

*Optional:* the model field to use as a unique ID for elasticsearch's
metadata ``_id``. Defaults to ``id`` (also called
```pk`` <https://docs.djangoproject.com/en/dev/topics/db/models/#automatic-primary-key-fields>`__).

Settings
--------
Add 'django_es' to INSTALLED_APPS.


SIGNAL_CLASS
~~~~~~~~~~~~

*Optional:* if it exists, it must be a dictionary (even empty), and will
connect to the ``pre_save``, ``post save``, ``pre delete`` model functions of *all*
models registered.
One may also define a signal processor class for more custom
functionality by placing the string value of the module path under a key
called ``SIGNAL_CLASS`` defining ``setup`` and ``teardown`` methods,
which take ``model`` as the only parameter. These methods connect and disconnect the signal
processing class to django signals (signals are connected to each model
registered).

Example with a customized ``SIGNAL_CLASS``

In the settings:

.. code:: python

    DJANGO_ES = {
        'SIGNAL_CLASS': '.signals.DjangoESSignalProcessor'
    }

In a separated file:

.. code:: python

    from django.db.models import signals

    class DjangoESSignalProcessor(object):

        @staticmethod
        def post_save_connector(sender, instance, created, **kwargs):
            from django_es.utils import update_index
            # Only create index if created
            if created:
                update_index([instance], sender, bulk_size=1)

        @staticmethod
        def pre_delete_connector(sender, instance, **kwargs):
            from django_es.utils import delete_index_item
            delete_index_item(instance, sender)

        def setup(self, model):
            signals.post_save.connect(self.post_save_connector, sender=model)
            signals.pre_delete.connect(self.pre_delete_connector, sender=model)

        def teardown(self, model):
            signals.pre_delete.disconnect(self.pre_delete_connector, sender=model)
            signals.post_save.disconnect(self.post_save_connector, sender=model)


BUFFER\_SIZE
^^^^^^^^^^^^

*Optional:* an integer representing the number of items to buffer before
making a bulk index update, defaults to ``100``.

**WARNING**: if your application is shut down before the buffer is
emptied, then any buffered instance *will not* be indexed on
elasticsearch. Hence, a possibly better implementation is wrapping
``post_save_connector`` and ``pre_delete_connector`` from
``django_es.signals`` in a celery task. It is not implemented as such
here in order to not require ``celery``.

