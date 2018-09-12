import json
from unittest import skip

from djangocms_moderation.helpers import (
    get_form_submission_for_step,
    get_page_or_404,
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
