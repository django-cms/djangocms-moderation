import mock

from django.contrib import admin

from cms.models import PageContent

from djangocms_versioning import versionables
from djangocms_versioning.admin import VersionAdmin
from djangocms_versioning.constants import PUBLISHED
from djangocms_versioning.test_utils.factories import PageVersionFactory

from .utils.base import BaseTestCase, MockRequest


class VersionAdminMonkeypatchTestCase(BaseTestCase):
    def setUp(self):
        versionable = versionables.for_content(PageContent)
        self.version_admin = VersionAdmin(versionable.version_model_proxy, admin.AdminSite())
        self.mock_request = MockRequest()
        self.mock_request.user = self.user
        super().setUp()

    @mock.patch('djangocms_moderation.monkeypatch.is_obj_review_locked')
    def test_get_edit_link(self, mock_is_obj_review_locked):
        """
        VersionAdmin should call moderation's version of _get_edit_link
        """
        mock_is_obj_review_locked.return_value = True
        edit_link = self.version_admin._get_edit_link(
            self.pg1_version, self.mock_request, disabled=False
        )
        # We test that moderation check is called when getting an edit link
        self.assertTrue(mock_is_obj_review_locked.called)
        # Edit link is blank as `mock_is_obj_review_locked` is True
        self.assertEqual(edit_link, '')

    @mock.patch('djangocms_moderation.monkeypatch.is_registered_for_moderation')
    @mock.patch('djangocms_moderation.monkeypatch.is_obj_review_locked')
    def test_get_edit_link_not_moderation_registered(self, mock_is_obj_review_locked,
                                                     mock_is_registered_for_moderation):
        """
        VersionAdmin should *not* call moderation's version of _get_edit_link
        """
        mock_is_registered_for_moderation.return_value = False
        mock_is_obj_review_locked.return_value = True
        edit_link = self.version_admin._get_edit_link(
            self.pg1_version, self.mock_request, disabled=False
        )

        # Edit link is not blanked out because moderation is not registered
        self.assertTrue(mock_is_registered_for_moderation.called)
        self.assertFalse(mock_is_obj_review_locked.called)
        self.assertNotEqual(edit_link, '')

    def test_get_state_actions(self):
        """
        Make sure publish actions is not present, and moderation actions
        were added
        """
        actions = self.version_admin.get_state_actions()
        action_names = [action.__name__ for action in actions]
        self.assertIn('_get_moderation_link', action_names)
        self.assertNotIn('_get_publish_link', action_names)

    def test_get_moderation_link(self):
        link = self.version_admin._get_moderation_link(
            self.pg1_version, self.mock_request
        )
        self.assertEqual(
            'In Moderation "{}"'.format(self.collection1.name),
            link
        )
        version = PageVersionFactory(state=PUBLISHED)
        link = self.version_admin._get_moderation_link(
            version, self.mock_request
        )
        self.assertEqual('', link)

        draft_version = PageVersionFactory(created_by=self.user3)
        # Request has self.user, so the moderation link won't be displayed.
        # This is version lock in place
        link = self.version_admin._get_moderation_link(
            draft_version, self.mock_request
        )
        self.assertEqual('', link)

        draft_version = PageVersionFactory(created_by=self.mock_request.user)
        # Now the version lock is lifted, so we should be able to add to moderation
        link = self.version_admin._get_moderation_link(
            draft_version, self.mock_request
        )
        self.assertIn('Submit for moderation', link)

    @mock.patch('djangocms_moderation.monkeypatch.is_registered_for_moderation')
    def test_get_moderation_link_when_not_registered(self, mock_is_registered_for_moderation):
        mock_is_registered_for_moderation.return_value = False

        link = self.version_admin._get_moderation_link(
            self.pg1_version, self.mock_request
        )
        self.assertEqual('', link)
