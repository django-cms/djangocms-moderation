import json
from unittest.mock import patch

from django.test import override_settings

from djangocms_moderation.helpers import (
    get_active_moderation_request,
    get_form_submission_for_step,
    get_page_or_404,
    get_workflow_or_none,
    is_moderation_enabled,
)
from djangocms_moderation.models import (
    ConfirmationPage,
    ConfirmationFormSubmission,
    PageModeration,
    Workflow,
)

from .utils import BaseTestCase


class GetWorkflowOrNoneTest(BaseTestCase):

    def test_existing_workflow(self):
        workflow = Workflow.objects.get(pk=1)
        self.assertEqual(get_workflow_or_none(1), workflow)
        workflow = Workflow.objects.get(pk=2)
        self.assertEqual(get_workflow_or_none(2), workflow)

    def test_non_existing_workflow(self):
        self.assertIsNone(get_workflow_or_none(10))


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


class IsModerationEnabledTest(BaseTestCase):

    @override_settings(CMS_MODERATION_ENABLE_WORKFLOW_OVERRIDE=True)
    def test_returns_true_with_override_no_moderation_object(self):
        self.assertTrue(is_moderation_enabled(self.pg1))

    @override_settings(CMS_MODERATION_ENABLE_WORKFLOW_OVERRIDE=True)
    def test_returns_true_with_override_moderation_object_enabled(self):
        PageModeration.objects.create(extended_object=self.pg1, enabled=True, workflow=self.wf1,)
        self.assertTrue(is_moderation_enabled(self.pg1))

    @override_settings(CMS_MODERATION_ENABLE_WORKFLOW_OVERRIDE=True)
    def test_returns_false_with_override_moderation_object_disabled(self):
        PageModeration.objects.create(extended_object=self.pg1, enabled=False, workflow=self.wf1,)
        self.assertFalse(is_moderation_enabled(self.pg1))

    @override_settings(CMS_MODERATION_ENABLE_WORKFLOW_OVERRIDE=True)
    def test_returns_false_with_override_no_workflows(self):
        Workflow.objects.all().delete()
        self.assertFalse(is_moderation_enabled(self.pg1))

    def test_returns_true_default_settings_has_default_workflow(self):
        self.assertTrue(is_moderation_enabled(self.pg1))

    def test_returns_true_default_settings_moderation_object_enabled(self):
        PageModeration.objects.create(extended_object=self.pg1, enabled=True, workflow=self.wf1,)
        self.assertTrue(is_moderation_enabled(self.pg1))

    def test_returns_false_default_settings_moderation_object_disabled(self):
        PageModeration.objects.create(extended_object=self.pg1, enabled=False, workflow=self.wf1,)
        self.assertFalse(is_moderation_enabled(self.pg1))

    @patch('djangocms_moderation.helpers.get_page_moderation_workflow', return_value=None)
    def test_returns_false_default_settings_no_workflow(self, mock_gpmw):
        self.assertFalse(is_moderation_enabled(self.pg1))


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
        cfs2 = ConfirmationFormSubmission.objects.create(
            request=self.moderation_request1,
            for_step=self.wf1st2,
            by_user=self.user,
            data=json.dumps([{'label': 'Question 1', 'answer': 'Yes'}]),
            confirmation_page=cp,
        )
        result = get_form_submission_for_step(active_request=self.moderation_request1, current_step=self.wf1st1,)
        self.assertEqual(result, cfs1)
