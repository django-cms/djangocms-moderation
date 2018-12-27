from djangocms_versioning.test_utils.factories import PageVersionFactory
from tests.utils.base import BaseTestCase

from djangocms_moderation.cms_config import ModerationExtension

from .utils.factories import (
    PlaceholderFactory,
    PollPluginFactory,
    PollVersionFactory,
)


class ConfigTestCase(BaseTestCase):

    def test_get_moderated_children_from_placeholder_has_only_registered_model(self):
        """
        The moderated model is only a model registered with moderation
        """
        pg_version = PageVersionFactory(created_by=self.user, content__language='en')

        # Populate page
        placeholder = PlaceholderFactory.create(source=pg_version.content)
        poll_version = PollVersionFactory(created_by=self.user)
        PollPluginFactory.create(placeholder=placeholder, poll=poll_version.content.poll)

        moderation_extension = ModerationExtension()
        moderated_children = moderation_extension.get_moderated_children_from_placeholder(placeholder)

        self.assertEqual(moderated_children, [poll_version])
