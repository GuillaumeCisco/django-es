from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _


class SimpleDjangoESConfig(AppConfig):
    """Simple AppConfig which does not do automatic discovery."""

    name = 'django_es'
    verbose_name = _("ElasticSearch Module")

    def ready(self):
        pass


class DjangoESConfig(SimpleDjangoESConfig):
    """The default AppConfig for Django ES which does autodiscovery."""

    def ready(self):
        super(DjangoESConfig, self).ready()
        self.module.autodiscover()
