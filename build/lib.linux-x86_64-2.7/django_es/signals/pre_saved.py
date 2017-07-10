from django.conf import settings
from _collections import defaultdict

from django.db.models import signals

__items_to_be_indexed__ = defaultdict(list)


class PreSavedDjangoESSignalProcessor(object):

    """
    Signal processor class which works with pre_save/post_save philosophy and database query (or cache)
    http://stackoverflow.com/questions/1355150/django-when-saving-how-can-you-check-if-a-field-has-changed
    """

    @staticmethod
    def pre_save_connector(sender, instance, **kwargs):
        try:
            obj = sender.objects.get(pk=instance.pk)
        except sender.DoesNotExist:
            pass  # Object is new, so field hasn't technically changed, but you may want to do something else here.
        else:
            if not obj.name == instance.name:  # Field has changed
                instance.to_update = True

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

        if created or instance.to_update:

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
        signals.pre_save.connect(self.pre_save_connector, sender=model)
        signals.post_save.connect(self.post_save_connector, sender=model)
        signals.pre_delete.connect(self.pre_delete_connector, sender=model)

    def teardown(self, model):
        signals.pre_delete.disconnect(self.pre_delete_connector, sender=model)
        signals.post_save.disconnect(self.post_save_connector, sender=model)
        signals.pre_save.disconnect(self.pre_save_connector, sender=model)
