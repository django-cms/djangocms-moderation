from unittest import mock

from djangocms_versioning.test_utils.factories import PageVersionFactory

from djangocms_moderation.helpers import is_obj_version_unlocked

from .utils.base import BaseTestCase


try:
    from djangocms_versioning.models import Version
except ImportError:
    Version = None


class VersionLockingTestCase(BaseTestCase):
    def test_is_obj_version_unlocked_after_publish(self):
        self.assertIsNotNone(Version)
        version = PageVersionFactory(created_by=self.user)
        self.assertTrue(is_obj_version_unlocked(version.content, self.user))
        self.assertFalse(is_obj_version_unlocked(version.content, self.user2))
        version.publish(self.user)
        # reload version to update cache
        version = Version.objects.get_for_content(version.content)
        self.assertTrue(is_obj_version_unlocked(version.content, self.user2))

        # Make sure that we are actually calling the version-lock method and it
        # still exists
        with mock.patch(
            "djangocms_moderation.helpers.content_is_unlocked_for_user"
        ) as _mock:
            is_obj_version_unlocked(version.content, self.user2)
            _mock.assert_called_once_with(version.content, self.user2)
