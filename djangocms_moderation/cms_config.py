from django.core.exceptions import ImproperlyConfigured

from cms.app_base import CMSAppConfig, CMSAppExtension
from cms.models import PageContent


class ModerationExtension(CMSAppExtension):
    def __init__(self):
        self.moderated_models = []
        self.moderation_request_changelist_actions = []
        self.moderation_request_changelist_fields = []

    def handle_moderation_request_changelist_actions(self, moderation_request_changelist_actions):
        self.moderation_request_changelist_actions.extend(moderation_request_changelist_actions)

    def handle_moderation_request_changelist_fields(self, moderation_request_changelist_fields):
        self.moderation_request_changelist_fields.extend(moderation_request_changelist_fields)

    def configure_app(self, cms_config):
        versioning_enabled = getattr(cms_config, "djangocms_versioning_enabled", False)
        moderated_models = getattr(cms_config, "moderated_models", [])

        if not versioning_enabled:
            raise ImproperlyConfigured("Versioning needs to be enabled for Moderation")

        self.moderated_models.extend(moderated_models)

        if hasattr(cms_config, "moderation_request_changelist_actions"):
            self.handle_moderation_request_changelist_actions(cms_config.moderation_request_changelist_actions)

        if hasattr(cms_config, "moderation_request_changelist_fields"):
            self.handle_moderation_request_changelist_fields(cms_config.moderation_request_changelist_fields)


class CoreCMSAppConfig(CMSAppConfig):
    djangocms_moderation_enabled = True
    djangocms_versioning_enabled = True
    moderated_models = [PageContent]
    versioning = []
