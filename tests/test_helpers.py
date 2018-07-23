import json

from djangocms_moderation.helpers import (
    get_active_moderation_request,
    get_form_submission_for_step,
    get_page_or_404,
)
from djangocms_moderation.models import (
    ConfirmationFormSubmission,
    ConfirmationPage,
)

from .utils import BaseTestCase


class GetCurrentModerationRequestTest(BaseTestCase):

    def test_existing_moderation_request(self):
        active_request = get_active_moderation_request(self.pg1, 'en')
        self.assertEqual(active_request, self.moderation_request1)

    def test_no_moderation_request(self):
        active_request = get_active_moderation_request(self.pg2, 'en')
        self.assertIsNone(active_request)


class GetPageOr404Test(BaseTestCase):

    def test_returns_page(self):
        self.assertEqual(get_page_or_404(self.pg1.pk, 'en'), self.pg1)


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
