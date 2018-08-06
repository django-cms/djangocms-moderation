try:
    from unittest.mock import Mock
except ImportError:
    from mock import Mock

from unittest import TestCase
from unittest.mock import patch

from django.apps import apps
from django.core.exceptions import ImproperlyConfigured

from cms import app_registration
from cms.test_utils.testcases import CMSTestCase
from cms.utils.setup import setup_cms_apps

from djangocms_moderation.cms_config import ModerationExtension

from .utils.app_1.models import App1PostContent, App1TitleContent
from .utils.app_2.models import App2PostContent, App2TitleContent


class CMSConfigTest(CMSTestCase, TestCase):

    def setUp(self):
        app_registration.get_cms_extension_apps.cache_clear()
        app_registration.get_cms_config_apps.cache_clear()

    def test_missing_versioning_enabled(self):
        extension = ModerationExtension()
        cms_config = Mock(
            moderated_models=[App1PostContent, App1TitleContent, App2PostContent, App2TitleContent],
            djangocms_moderation_enabled=True,
            djangocms_versioning_enabled=False,
            app_config=Mock(label='blah_cms_config')
        )

        with self.assertRaises(ImproperlyConfigured) as improperly_configured:
            extension.configure_app(cms_config)
            self.assertEqual(improperly_configured.exception, 'Versioning needs to be enabled for Moderation')

    @patch('django.apps.apps.get_app_config')
    def test_model_not_in_versionables_by_content(self, get_app_config):
        extension = ModerationExtension()
        cms_config = Mock(
            moderated_models=[App1PostContent],
            djangocms_moderation_enabled=True,
            djangocms_versioning_enabled=True,
            app_config=Mock(label='blah_cms_config')
        )

        with self.assertRaises(ImproperlyConfigured) as improperly_configured:
            extension.configure_app(cms_config)
            self.assertContains(improperly_configured.exception,
                                'Moderated model %s need to be Versionable' % str(App1PostContent))


class CMSConfigIntegrationTest(CMSTestCase):

    def setUp(self):
        app_registration.get_cms_extension_apps.cache_clear()
        app_registration.get_cms_config_apps.cache_clear()
        self.moderated_models = (App2PostContent, App2TitleContent,
                                 App1PostContent, App1TitleContent)

    def test_config_with_two_apps(self):
        setup_cms_apps()
        moderation_config = apps.get_app_config('djangocms_moderation')
        registered_model = moderation_config.cms_extension.moderated_models

        for model in self.moderated_models:
            self.assertIn(model, registered_model)

        self.assertEqual(len(registered_model), 4)
