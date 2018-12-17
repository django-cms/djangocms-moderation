from django.apps import apps
from django.core.exceptions import ImproperlyConfigured

from cms.app_base import CMSAppConfig, CMSAppExtension
from cms.models import PageContent
from cms.utils.plugins import downcast_plugins

from djangocms_versioning import versionables
from djangocms_versioning.constants import DRAFT
from djangocms_versioning.models import Version


class ModerationExtension(CMSAppExtension):

    def __init__(self):
        self.moderated_models = []

    def configure_app(self, cms_config):
        versioning_enabled = getattr(cms_config, 'djangocms_versioning_enabled', False)
        moderated_models = getattr(cms_config, 'moderated_models', [])

        if not versioning_enabled:
            raise ImproperlyConfigured('Versioning needs to be enabled for Moderation')

        versioning_extension = apps.get_app_config('djangocms_versioning').cms_extension
        for model in moderated_models:
            # @todo replace this with a to be provided func from versioning_extensions
            if model not in versioning_extension.versionables_by_content:
                raise ImproperlyConfigured(
                    'Moderated model %s need to be Versionable, please include every model that '
                    'needs to be moderated in djangocms_versioning VersionableItem entry' % model
                )

        self.moderated_models.extend(moderated_models)

    def get_moderated_children_from_placeholder(self, placeholder, language=None):

        for plugin in downcast_plugins(placeholder.get_plugins()):

            plugin_model = plugin.get_plugin_class().model._meta

            candidate_fields = [
                f for f in plugin_model.get_fields()
                if f.is_relation and not f.auto_created
            ]

            for field in candidate_fields:
                try:
                    field_instance = getattr(plugin, field.name)
                    versionable = versionables.for_grouper(field_instance)  # (field.remote_field.model)
                except KeyError:
                    continue

                if versionable.content_model in self.moderated_models:
                    # Get the draft version if it exists
                    versions = Version.objects.filter_by_grouper(field_instance).filter(state=DRAFT)

                    #FIXME: Grouping values???
                    # fields = versionable.grouping_values(content)
                    # content_objects = versionable.for_grouping_values(**fields)

                    print("Draft found")


class CoreCMSAppConfig(CMSAppConfig):
    djangocms_moderation_enabled = True
    djangocms_versioning_enabled = True
    moderated_models = [
        PageContent,
    ]
    versioning = []
