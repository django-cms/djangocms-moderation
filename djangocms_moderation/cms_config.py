from django.apps import apps
from django.core.exceptions import ImproperlyConfigured

from cms.app_base import CMSAppExtension


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
