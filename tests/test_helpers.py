import json
import mock
from unittest import skip

from django.core.urlresolvers import reverse

from djangocms_versioning.test_utils.factories import PageVersionFactory

from djangocms_moderation.constants import COLLECTING, IN_REVIEW
from djangocms_moderation.helpers import (
    get_form_submission_for_step,
    get_moderation_button_title_and_url,
    get_page_or_404,
    is_obj_version_unlocked,
)
from djangocms_moderation.models import (
    ConfirmationFormSubmission,
    ConfirmationPage,
    ModerationCollection, ModerationRequest)

from .utils.base import BaseTestCase


@skip("Confirmation page feature doesn't support 1.0.x yet")
class GetPageOr404Test(BaseTestCase):
    def test_returns_page(self):
        self.assertEqual(get_page_or_404(self.pg1_version.pk, 'en'), self.pg1_version)


class GetFormSubmissions(BaseTestCase):
    def test_returns_form_submission_for_step(self):
        cp = ConfirmationPage.objects.create(
            name='Checklist Form',
        )
        self.role1.confirmation_page = cp
        self.role1.save()

        cfs1 = ConfirmationFormSubmission.objects.create(
            moderation_request=self.moderation_request1,
            for_step=self.wf1st1,
            by_user=self.user,
            data=json.dumps([{'label': 'Question 1', 'answer': 'Yes'}]),
            confirmation_page=cp,
        )
        ConfirmationFormSubmission.objects.create(
            moderation_request=self.moderation_request1,
            for_step=self.wf1st2,
            by_user=self.user,
            data=json.dumps([{'label': 'Question 1', 'answer': 'Yes'}]),
            confirmation_page=cp,
        )
        result = get_form_submission_for_step(active_request=self.moderation_request1, current_step=self.wf1st1,)
        self.assertEqual(result, cfs1)


class VersionLockingTestCase(BaseTestCase):
    def test_is_obj_version_unlocked(self):
        version = PageVersionFactory(created_by=self.user)
        self.assertTrue(is_obj_version_unlocked(version.content, self.user))
        self.assertFalse(is_obj_version_unlocked(version.content, self.user2))
        version.publish(self.user)
        self.assertTrue(is_obj_version_unlocked(version.content, self.user2))

        # Make sure that we are actually calling the version-lock method and it
        # still exists
        with mock.patch('djangocms_moderation.helpers.content_is_unlocked_for_user') as _mock:
            is_obj_version_unlocked(version.content, self.user2)
            _mock.assert_called_once_with(version.content, self.user2)

    def test_is_obj_version_unlocked_when_locking_is_not_installed(self):
        with mock.patch('djangocms_moderation.helpers.content_is_unlocked_for_user') as _mock:
            _mock = None  # noqa
            version = PageVersionFactory(created_by=self.user)
            self.assertTrue(is_obj_version_unlocked(version.content, self.user3))


class ModerationButtonLinkAndUrlTestCase(BaseTestCase):
    def setUp(self):
        self.collection = ModerationCollection.objects.create(
            author=self.user, name='C1', workflow=self.wf1, status=COLLECTING
        )
        version = PageVersionFactory(created_by=self.user)

        self.collection.add_version(version)

        self.mr = ModerationRequest.objects.get(
            version=version, collection=self.collection
        )
        self.expected_url = "{}?collection__id__exact={}".format(
            reverse('admin:djangocms_moderation_moderationrequest_changelist'),
            self.collection.id,
        )

    def test_get_moderation_button_title_and_url_when_collection(self):
        title, url = get_moderation_button_title_and_url(self.mr)
        self.assertEqual(
            title,
            'In collection "C1 ({})"'.format(self.collection.id)
        )
        self.assertEqual(url, self.expected_url)

    def test_get_moderation_button_title_and_url_when_in_review(self):
        self.collection.status = IN_REVIEW
        self.collection.save()

        title, url = get_moderation_button_title_and_url(self.mr)
        self.assertEqual(
            title,
            'In moderation "C1 ({})"'.format(self.collection.id)
        )
        self.assertEqual(url, self.expected_url)

    def test_get_moderation_button_truncated_title_and_url(self):
        self.collection.name = 'Very long collection name so long wow!'
        self.collection.save()
        title, url = get_moderation_button_title_and_url(self.mr)
        self.assertEqual(
            title,
            # Default limit is 24 characters
            'In collection "Very long collection nam... ({})"'.format(
                self.collection.id,
             )
        )
        with mock.patch('djangocms_moderation.helpers.COLLECTION_NAME_LENGTH_LIMIT', 3):
            title, url = get_moderation_button_title_and_url(self.mr)
            self.assertEqual(
                title,
                'In collection "Ver... ({})"'.format(
                    self.collection.id,
                 )
            )

        with mock.patch('djangocms_moderation.helpers.COLLECTION_NAME_LENGTH_LIMIT', None):
            # None means no limit
            title, url = get_moderation_button_title_and_url(self.mr)
            self.assertEqual(
                title,
                'In collection "Very long collection name so long wow! ({})"'.format(
                    self.collection.id,
                 )
            )

        self.assertEqual(url, self.expected_url)

