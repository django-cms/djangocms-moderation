from django.apps import apps
from django.core.exceptions import ImproperlyConfigured

from cms.app_base import CMSAppConfig, CMSAppExtension
from cms.models import PageContent

from djangocms_versioning import versionables
from djangocms_versioning.constants import DRAFT


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

    def get_moderated_children_from_placeholder(self, placeholder):

        for plugin in placeholder.get_plugins():

            plugin_model = plugin.get_plugin_class().model._meta

            candidate_fields = [
                f for f in plugin_model.get_fields()
                if f.is_relation and not f.auto_created and f.verbose_name == 'alias'
            ]

            for field in candidate_fields:
                try:
                    minimize_looping = plugin_model.get_field('alias')
                    versionable = versionables.for_grouper(field.remote_field.model)
                except KeyError:
                    continue

                if versionable.content_model in self.moderated_models:
                    # Is the version draft??

                    from .models import Version

                    result_set = versionable.content_model._base_manager.filter(
                        versions__state__in=(DRAFT),
                    ).order_by('versions__state')

                    #version = Version.objects.get_for_content(versionable.content_model)

                    print("Find draft")


class CoreCMSAppConfig(CMSAppConfig):
    djangocms_moderation_enabled = True
    djangocms_versioning_enabled = True
    moderated_models = [
        PageContent,
    ]
    versioning = []
