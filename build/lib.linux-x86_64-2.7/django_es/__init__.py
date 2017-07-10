from django.conf import settings
from django.contrib.admin.decorators import register
from django.utils.module_loading import autodiscover_modules
from elasticsearch import Elasticsearch

__author__ = 'guillaume'

# cache es_instance
es_instance = getattr(settings, 'ES_CLIENT', Elasticsearch())

# This import need to be placed after for avoiding circular dependencies
from .mappings import IndexMapping, mapping, ModelIndex


__all__ = [
    "register", "ModelIndex", "IndexMapping", "mapping", "autodiscover",
]


def autodiscover():
    autodiscover_modules('djangoes', register_to=mapping)


default_app_config = 'django_es.apps.DjangoESConfig'
