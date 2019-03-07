from django.core.exceptions import ImproperlyConfigured

from cms.app_base import CMSAppConfig, CMSAppExtension
from cms.models import PageContent


class ModerationExtension(CMSAppExtension):
    def __init__(self):
        self.moderated_models = []

    def configure_app(self, cms_config):
        versioning_enabled = getattr(cms_config, "djangocms_versioning_enabled", False)
        moderated_models = getattr(cms_config, "moderated_models", [])

        if not versioning_enabled:
            raise ImproperlyConfigured("Versioning needs to be enabled for Moderation")

        self.moderated_models.extend(moderated_models)


class CoreCMSAppConfig(CMSAppConfig):
    djangocms_moderation_enabled = True
    djangocms_versioning_enabled = True
    moderated_models = [PageContent]
    versioning = []
