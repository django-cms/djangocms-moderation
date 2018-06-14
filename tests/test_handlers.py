import re
from unittest.mock import MagicMock, patch

from djangocms_moderation.handlers import *

from .utils import BaseTestCase


class ModerationConfirmationFormSubmissionTest(BaseTestCase):

    def test_throws_exception_when_form_data_is_invalid(self):
        with self.assertRaises(ValueError) as context:
            moderation_confirmation_form_submission(
                sender='test',
                page_id=self.pg1.pk,
                language='en',
                user=self.user,
                form_data=[{'label': 'Question 1', 'answer': 'Yes'}]
            )
        self.assertTrue('Each field dict should contain label and value keys.' in str(context.exception))

    def test_creates_new_form_submission_when_form_data_is_valid(self):
        moderation_confirmation_form_submission(
            sender='test',
            page_id=self.pg1.pk,
            language='en',
            user=self.user,
            form_data=[{'label': 'Question 1', 'value': 'Yes'}]
        )
        result = ConfirmationFormSubmission.objects.filter(request=self.moderation_request1)
        self.assertEqual(len(result), 1)
