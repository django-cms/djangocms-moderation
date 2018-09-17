from unittest import skip

from djangocms_moderation.contrib.moderation_forms.cms_plugins import (
    ModerationFormPlugin,
)
from djangocms_moderation.handlers import (
    moderation_confirmation_form_submission,
)
from djangocms_moderation.models import (
    ConfirmationFormSubmission,
    ConfirmationPage,
)

from .utils.base import BaseTestCase


@skip("Confirmation page feature doesn't support 1.0.x yet")
class ModerationConfirmationFormSubmissionTest(BaseTestCase):

    def setUp(self):
        self.cp = ConfirmationPage.objects.create(
            name='Checklist Form',
        )
        self.role1.confirmation_page = self.cp
        self.role1.save()

    def test_throws_exception_when_form_data_is_invalid(self):
        with self.assertRaises(ValueError) as context:
            moderation_confirmation_form_submission(
                sender=ModerationFormPlugin,
                page=self.pg1_version,
                language='en',
                user=self.user,
                form_data=[{'label': 'Question 1', 'answer': 'Yes'}]
            )
        self.assertTrue('Each field dict should contain label and value keys.' in str(context.exception))

    def test_creates_new_form_submission_when_form_data_is_valid(self):
        moderation_confirmation_form_submission(
            sender=ModerationFormPlugin,
            page=self.pg1_version,
            language='en',
            user=self.user,
            form_data=[{'label': 'Question 1', 'value': 'Yes'}],
        )
        result = ConfirmationFormSubmission.objects.filter(request=self.moderation_request1)
        self.assertEqual(result.count(), 1)
