from django.conf import settings
from _collections import defaultdict

from django.db.models import signals

__items_to_be_indexed__ = defaultdict(list)


class HasChangedDjangoESSignalProcessor(object):

    """
    Signal processor class which works with @track_data('name') on model declaration:
    http://cramer.io/2010/12/06/tracking-changes-to-fields-in-django/
    """

    @staticmethod
    def post_save_connector(sender, instance, created, **kwargs):

        """
        Be careful, if server is shut down unexpectedly, remaining items in buffer will be lost.
        Use a queue/task managing tool like celery.
        :param sender:
        :param instance:
        :param kwargs:
        :return:
        """

        from ..utils import update_index
        if created or instance.has_changed('name'):
            buffer_size = 100
            if hasattr(settings, 'DJANGO_ES') and 'BUFFER_SIZE' in settings.DJANGO_ES:
                buffer_size = settings.DJANGO_ES['BUFFER_SIZE']

            __items_to_be_indexed__[sender].append(instance)

            if len(__items_to_be_indexed__[sender]) >= buffer_size:
                update_index(__items_to_be_indexed__[sender], sender, bulk_size=buffer_size)
                # Let's now empty this buffer or we'll end up reindexing every item which was previously buffered.
                __items_to_be_indexed__[sender] = []

    @staticmethod
    def pre_delete_connector(sender, instance, **kwargs):
        from ..utils import delete_index_item
        delete_index_item(instance, sender)

    def setup(self, model):
        signals.post_save.connect(self.post_save_connector, sender=model)
        signals.pre_delete.connect(self.pre_delete_connector, sender=model)

    def teardown(self, model):
        signals.pre_delete.disconnect(self.pre_delete_connector, sender=model)
        signals.post_save.disconnect(self.post_save_connector, sender=model)
