from django.contrib import admin
from django.core.exceptions import ImproperlyConfigured

from cms.app_base import CMSAppConfig, CMSAppExtension
from cms.models import PageContent

from .admin_actions import add_items_to_collection


class ModerationExtension(CMSAppExtension):
    def __init__(self):
        self.moderated_models = []
        self.moderation_request_changelist_actions = []
        self.moderation_request_changelist_fields = []

    def handle_moderation_request_changelist_actions(self, moderation_request_changelist_actions):
        self.moderation_request_changelist_actions.extend(moderation_request_changelist_actions)

    def handle_moderation_request_changelist_fields(self, moderation_request_changelist_fields):
        self.moderation_request_changelist_fields.extend(moderation_request_changelist_fields)

    def handle_admin_actions(self, moderated_models):
        """
        Add items to collection to admin actions in model admin
        """
        for model in moderated_models:
            if admin.site.is_registered(model):
                admin_instance = admin.site._registry[model]
                admin_instance.actions = admin_instance.actions or []
                admin_instance.actions.append(add_items_to_collection)

    def configure_app(self, cms_config):
        versioning_enabled = getattr(cms_config, "djangocms_versioning_enabled", False)
        moderated_models = getattr(cms_config, "moderated_models", [])

        if not versioning_enabled:
            raise ImproperlyConfigured("Versioning needs to be enabled for Moderation")

        self.moderated_models.extend(moderated_models)
        if moderated_models:
            self.handle_admin_actions(moderated_models)

        if hasattr(cms_config, "moderation_request_changelist_actions"):
            self.handle_moderation_request_changelist_actions(cms_config.moderation_request_changelist_actions)

        if hasattr(cms_config, "moderation_request_changelist_fields"):
            self.handle_moderation_request_changelist_fields(cms_config.moderation_request_changelist_fields)


class CoreCMSAppConfig(CMSAppConfig):
    djangocms_moderation_enabled = True
    djangocms_versioning_enabled = True
    moderated_models = [PageContent]
    versioning = []
