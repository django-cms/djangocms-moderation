from django.test.client import RequestFactory

from djangocms_versioning.test_utils.factories import PageVersionFactory

from djangocms_moderation import utils
from djangocms_moderation.constants import ACTION_REJECTED, ACTION_STARTED
from djangocms_moderation.helpers import (
    get_active_moderation_request,
    is_obj_review_locked,
)
from djangocms_moderation.models import ModerationCollection, ModerationRequest
from tests.utils.base import BaseTestCase


class UtilsTestCase(BaseTestCase):
    def setUp(self):
        self.rf = RequestFactory()

    def test_extract_filter_param_from_changelist_url(self):
        mock_request = self.rf.get(
            "/admin/djangocms_moderation/collectioncomment/add/?_changelist_filters=collection__id__exact%3D1"
        )
        collection_id = utils.extract_filter_param_from_changelist_url(
            mock_request, "_changelist_filters", "collection__id__exact"
        )
        self.assertEqual(collection_id, "1")

        mock_request = self.rf.get(
            "/admin/djangocms_moderation/collectioncomment/add/?_changelist_filters=collection__id__exact%3D4"
        )
        collection_id = utils.extract_filter_param_from_changelist_url(
            mock_request, "_changelist_filters", "collection__id__exact"
        )
        self.assertEqual(collection_id, "4")

        mock_request = self.rf.get(
            "/admin/djangocms_moderation/requestcomment/add/?_changelist_filters=moderation_request__id__exact%3D1"
        )
        action_id = utils.extract_filter_param_from_changelist_url(
            mock_request, "_changelist_filters", "moderation_request__id__exact"
        )
        self.assertEqual(action_id, "1")

        mock_request = self.rf.get(
            "/admin/djangocms_moderation/requestcomment/add/?_changelist_filters=moderation_request__id__exact%3D2"
        )
        action_id = utils.extract_filter_param_from_changelist_url(
            mock_request, "_changelist_filters", "moderation_request__id__exact"
        )
        self.assertEqual(action_id, "2")

    def test_get_active_moderation_request(self):
        self.assertEqual(
            self.moderation_request1,
            get_active_moderation_request(self.pg1_version.content),
        )
        version = PageVersionFactory()
        # Inactive request with this version
        ModerationRequest.objects.create(
            version=version,
            collection=self.collection1,
            is_active=False,
            author=self.user,
        )
        self.assertIsNone(get_active_moderation_request(version.content))


class TestReviewLock(BaseTestCase):
    def test_is_obj_review_locked(self):
        page_version = PageVersionFactory()

        page_content = page_version.content
        self.assertFalse(is_obj_review_locked(page_content, self.user))
        self.assertFalse(is_obj_review_locked(page_content, self.user2))
        self.assertFalse(is_obj_review_locked(page_content, self.user3))

        collection = ModerationCollection.objects.create(
            author=self.user, name="My collection 1", workflow=self.wf1
        )
        collection.add_version(page_version)
        # Now the version is part of the collection so it is review locked
        self.assertTrue(is_obj_review_locked(page_content, self.user))
        self.assertTrue(is_obj_review_locked(page_content, self.user2))
        self.assertTrue(is_obj_review_locked(page_content, self.user3))

        mr = ModerationRequest.objects.get(collection=collection)
        mr.actions.create(by_user=self.user, action=ACTION_STARTED)

        # Now we reject the moderation request, which means that `user` can
        # resubmit the changes, the review lock is lifted for them
        mr.actions.create(by_user=self.user2, action=ACTION_REJECTED)
        self.assertFalse(is_obj_review_locked(page_content, self.user))
        self.assertTrue(is_obj_review_locked(page_content, self.user2))
        self.assertTrue(is_obj_review_locked(page_content, self.user3))
