from base import *
from has_changed import *
from importlib import import_module

__author__ = 'guillaume'


def get_signal_processor():

    if hasattr(settings, 'DJANGO_ES') and 'SIGNAL_CLASS' in settings.DJANGO_ES:
        signal_path = settings.DJANGO_ES['SIGNAL_CLASS'].split('.')
        signal_module = import_module('.'.join(signal_path[:-1]))
        signal_class = getattr(signal_module, signal_path[-1])
    else:
        signal_class = BaseDjangoESSignalProcessor
    return signal_class()
