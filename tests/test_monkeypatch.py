from unittest import mock

from django.contrib import admin
from django.urls import reverse

from cms.models import PageContent
from cms.models.fields import PlaceholderRelationField

from djangocms_versioning import __version__ as versioning_version, versionables
from djangocms_versioning.admin import VersionAdmin
from djangocms_versioning.constants import DRAFT, PUBLISHED
from djangocms_versioning.test_utils.factories import (
    PageVersionFactory,
    PlaceholderFactory,
)

from djangocms_moderation.helpers import is_obj_version_unlocked
from djangocms_moderation.monkeypatch import _is_placeholder_review_unlocked

from .utils.base import BaseTestCase, MockRequest


class VersionAdminMonkeypatchTestCase(BaseTestCase):
    def setUp(self):
        versionable = versionables.for_content(PageContent)
        self.version_admin = VersionAdmin(
            versionable.version_model_proxy, admin.AdminSite()
        )
        self.mock_request = MockRequest()
        self.mock_request.user = self.user
        super().setUp()

    @mock.patch("djangocms_moderation.monkeypatch.is_obj_review_locked")
    def test_get_edit_link(self, mock_is_obj_review_locked):
        """
        VersionAdmin should call moderation's version of _get_edit_link
        """
        pg1_version = PageVersionFactory(created_by=self.mock_request.user)
        mock_is_obj_review_locked.return_value = True
        edit_link = self.version_admin._get_edit_link(
            pg1_version, self.mock_request, disabled=False
        )
        # We test that moderation check is called when getting an edit link
        self.assertTrue(mock_is_obj_review_locked.called)
        if versioning_version >= "2.0.2":
            self.assertEqual("", edit_link)
        else:
            self.assertIn("inactive", edit_link)

    @mock.patch("djangocms_moderation.monkeypatch.is_registered_for_moderation")
    @mock.patch("djangocms_moderation.monkeypatch.is_obj_review_locked")
    def test_get_edit_link_not_moderation_registered(
        self, mock_is_obj_review_locked, mock_is_registered_for_moderation
    ):
        """
        VersionAdmin should *not* call moderation's version of _get_edit_link
        """
        pg1_version = PageVersionFactory(created_by=self.mock_request.user)
        mock_is_registered_for_moderation.return_value = False
        mock_is_obj_review_locked.return_value = True
        edit_link = self.version_admin._get_edit_link(
            pg1_version, self.mock_request, disabled=False
        )

        # Edit link is not blanked out because moderation is not registered
        self.assertTrue(mock_is_registered_for_moderation.called)
        self.assertFalse(mock_is_obj_review_locked.called)
        self.assertNotEqual(edit_link, "")

    @mock.patch("djangocms_moderation.monkeypatch.is_obj_review_locked")
    def test_get_archive_link(self, _mock):
        """
        VersionAdmin should call moderation's version of _get_archive_link
        """
        version = PageVersionFactory(state=DRAFT, created_by=self.user)
        archive_url = reverse(
            "admin:{app}_{model}version_archive".format(
                app=version._meta.app_label, model=version.content._meta.model_name
            ),
            args=(version.pk,),
        )
        _mock.return_value = True
        if versioning_version != "2.0.0":
            archive_link = self.version_admin._get_archive_link(version, self.mock_request)
        else:
            # Bug in djangocms-verisoning 2.0.0: _get_archive_link does not call check_archive
            # So we do it by hand
            version.check_archive.as_bool(self.mock_request.user)
            archive_link = ""
        # We test that moderation check is called when getting an edit link
        self.assertEqual(1, _mock.call_count)
        self.assertIn("inactive", archive_link)

        _mock.return_value = None
        archive_link = self.version_admin._get_archive_link(version, self.mock_request)
        # We test that moderation check is called when getting the link
        if versioning_version != "2.0.0":
            self.assertEqual(2, _mock.call_count)
        # Archive link is active there as `get_active_moderation_request` is None
        self.assertNotIn("inactive", archive_link)
        self.assertIn(archive_url, archive_link)

    def test_get_state_actions(self):
        """
        Make sure publish actions is not present, and moderation actions
        were added
        """
        actions = self.version_admin.get_state_actions()
        action_names = [action.__name__ for action in actions]
        self.assertIn("_get_moderation_link", action_names)
        self.assertNotIn("_get_publish_link", action_names)

    def test_get_moderation_link(self):
        link = self.version_admin._get_moderation_link(
            self.pg1_version, self.mock_request
        )
        self.assertIn(
            "In collection &quot;{} ({})&quot;".format(
                self.collection1.name, self.collection1.id
            ),
            link,
        )
        version = PageVersionFactory(state=PUBLISHED)
        link = self.version_admin._get_moderation_link(version, self.mock_request)
        self.assertEqual("", link)

        draft_version = PageVersionFactory(created_by=self.user3)
        # Request has self.user, so the moderation link won't be displayed.
        # This is version lock in place
        self.assertFalse(is_obj_version_unlocked(draft_version.content, self.user))
        link = self.version_admin._get_moderation_link(draft_version, self.mock_request)
        self.assertEqual("", link)

        draft_version = PageVersionFactory(created_by=self.mock_request.user)
        # Now the version lock is lifted, so we should be able to add to moderation
        link = self.version_admin._get_moderation_link(draft_version, self.mock_request)
        self.assertIn("Submit for moderation", link)

    @mock.patch("djangocms_moderation.monkeypatch.is_registered_for_moderation")
    def test_get_moderation_link_when_not_registered(
        self, mock_is_registered_for_moderation
    ):
        mock_is_registered_for_moderation.return_value = False

        link = self.version_admin._get_moderation_link(
            self.pg1_version, self.mock_request
        )
        self.assertEqual("", link)

    @mock.patch("djangocms_moderation.monkeypatch.is_registered_for_moderation", return_value=True)
    def test_get_publish_link_when_registered(self, mock_is_registered_for_moderation):
        link = self.version_admin._get_publish_link(self.pg1_version, self.mock_request)
        self.assertEqual("", link)

    @mock.patch("djangocms_moderation.monkeypatch.is_registered_for_moderation", return_value=False)
    def test_get_publish_link_when_not_registered(self, mock_is_registered_for_moderation):
        link = self.version_admin._get_publish_link(self.pg1_version, self.mock_request)
        publish_url = reverse(
            "admin:{app}_{model}version_publish".format(
                app=self.pg1_version._meta.app_label,
                model=self.pg1_version.content._meta.model_name,
            ),
            args=(self.pg1_version.pk,),
        )
        self.assertNotEqual("", link)
        self.assertIn(publish_url, link)


class PlaceholderChecksTestCase(BaseTestCase):
    @mock.patch("djangocms_moderation.monkeypatch.is_registered_for_moderation")
    @mock.patch("djangocms_moderation.monkeypatch.is_obj_review_locked")
    def test_is_placeholder_review_unlocked(
        self, mock_is_registered_for_moderation, mock_is_obj_review_locked
    ):
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
            _is_placeholder_review_unlocked, PlaceholderRelationField.default_checks
        )
