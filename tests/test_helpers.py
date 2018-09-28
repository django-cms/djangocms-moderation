import json
import mock
from unittest import skip

from djangocms_versioning.test_utils.factories import PageVersionFactory

from djangocms_moderation.helpers import (
    get_form_submission_for_step,
    get_page_or_404,
    is_content_unlocked_for_user,
)
from djangocms_moderation.models import (
    ConfirmationFormSubmission,
    ConfirmationPage,
)

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
            request=self.moderation_request1,
            for_step=self.wf1st1,
            by_user=self.user,
            data=json.dumps([{'label': 'Question 1', 'answer': 'Yes'}]),
            confirmation_page=cp,
        )
        ConfirmationFormSubmission.objects.create(
            request=self.moderation_request1,
            for_step=self.wf1st2,
            by_user=self.user,
            data=json.dumps([{'label': 'Question 1', 'answer': 'Yes'}]),
            confirmation_page=cp,
        )
        result = get_form_submission_for_step(active_request=self.moderation_request1, current_step=self.wf1st1,)
        self.assertEqual(result, cfs1)


class VersionLockingTestCase(BaseTestCase):
    def test_version_locking_content_is_unlocked_for_user_exists(self):
        try:
            from djangocms_version_locking.helpers import content_is_unlocked_for_user
        except ImportError:
            self.fail("is_content_unlocked_for_user doesn't exist in "
                      "'djangocms_version_locking.helpers' anymore ")

    def test_is_content_unlocked_for_user(self):
        version = PageVersionFactory(created_by=self.user)
        self.assertTrue(is_content_unlocked_for_user(version.content, self.user))
        self.assertFalse(is_content_unlocked_for_user(version.content, self.user2))
        version.publish(self.user)
        self.assertTrue(is_content_unlocked_for_user(version.content, self.user2))

        with mock.patch('djangocms_version_locking.helpers.content_is_unlocked_for_user') as _mock:
            is_content_unlocked_for_user(version.content, self.user2)
            self.assertTrue(_mock.called)
