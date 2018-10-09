import mock

from django.contrib import admin
from django.urls import reverse

from cms.api import create_page
from cms.models import PageContent
from cms.models.fields import PlaceholderRelationField
from django.conf import settings
from django.utils.translation import ugettext_lazy as _

from djangocms_versioning import versionables
from djangocms_versioning.models import Version
from djangocms_versioning.admin import VersionAdmin
from djangocms_versioning.constants import DRAFT, PUBLISHED
from djangocms_versioning.test_utils.factories import PageVersionFactory, PlaceholderFactory

from djangocms_moderation.monkeypatch import _is_placeholder_review_unlocked

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
        # Edit link is inactive as `mock_is_obj_review_locked` is True
        self.assertIn('inactive', edit_link)

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

    @mock.patch('djangocms_moderation.monkeypatch.get_active_moderation_request')
    def test_get_archive_link(self, _mock):
        """
        VersionAdmin should call moderation's version of _get_archive_link
        """
        archive_url = reverse('admin:{app}_{model}version_archive'.format(
            app=self.pg1_version._meta.app_label,
            model=self.pg1_version.content._meta.model_name,
        ), args=(self.pg1_version.pk,))

        _mock.return_value = True
        archive_link = self.version_admin._get_archive_link(
            self.pg1_version, self.mock_request
        )
        # We test that moderation check is called when getting an edit link
        self.assertEqual(1, _mock.call_count)
        # Edit link is inactive as `get_active_moderation_request` is True
        self.assertIn('inactive', archive_link)
        self.assertNotIn(archive_url, archive_link)

        _mock.return_value = None
        archive_link = self.version_admin._get_archive_link(
            self.pg1_version, self.mock_request
        )
        # We test that moderation check is called when getting the link
        self.assertEqual(2, _mock.call_count)
        # Archive link is active there as `get_active_moderation_request` is None
        self.assertNotIn('inactive', archive_link)
        self.assertIn(archive_url, archive_link)

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


class PlaceholderChecksTestCase(BaseTestCase):

    @mock.patch('djangocms_moderation.monkeypatch.is_registered_for_moderation')
    @mock.patch('djangocms_moderation.monkeypatch.is_obj_review_locked')
    def test_is_placeholder_review_unlocked(self, mock_is_registered_for_moderation, mock_is_obj_review_locked):
        """
        Check that the monkeypatch returns expected value
        """
        version = PageVersionFactory()
        placeholder = PlaceholderFactory.create(source=version.content)

        mock_is_registered_for_moderation.return_value = True
        mock_is_obj_review_locked.return_value = True

        self.assertFalse(_is_placeholder_review_unlocked(placeholder, self.user))

        mock_is_registered_for_moderation.return_value = True
        mock_is_obj_review_locked.return_value = False

        self.assertTrue(_is_placeholder_review_unlocked(placeholder, self.user))

        mock_is_registered_for_moderation.return_value = False
        mock_is_obj_review_locked.return_value = True

        self.assertTrue(_is_placeholder_review_unlocked(placeholder, self.user))

    def test_function_added_to_checks_framework(self):
        """
        Check that the method has been added to the checks framework 
        """
        self.assertIn(
            _is_placeholder_review_unlocked,
            PlaceholderRelationField.default_checks,
        )

