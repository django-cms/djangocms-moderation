from django.test import TestCase, override_settings

from djangocms_moderation.helpers import *
from djangocms_moderation.models import Workflow, PageModeration

from .utils import BaseTestCase


class GetWorkflowByIdTest(BaseTestCase):

    def test_existing_workflow(self):
        workflow = Workflow.objects.get(pk=1)
        self.assertEqual(get_workflow_by_id(1), workflow)
        workflow = Workflow.objects.get(pk=2)
        self.assertEqual(get_workflow_by_id(2), workflow)

    def test_non_existing_workflow(self):
        self.assertIsNone(get_workflow_by_id(10))


class GetCurrentModerationRequestTest(BaseTestCase):

    def test_existing_moderation_request(self):
        active_request = get_current_moderation_request(self.pg1, 'en')
        self.assertEqual(active_request, self.moderation_request1)

    def test_no_moderation_request(self):
        active_request = get_current_moderation_request(self.pg2, 'en')
        self.assertIsNone(active_request)


class GetPageOr404Test(BaseTestCase):

    def test_returns_page(self):
        self.assertEqual(get_page_or_404(self.pg1.pk, 'en'), self.pg1)


class CanPageBeModerated(BaseTestCase):

    def test_returns_true_if_not_disabled_moderation(self):
        PageModeration.objects.create(
            extended_object=self.pg1,
            disable_moderation=False
        )
        self.assertTrue(can_page_be_moderated(self.pg1))

    def test_returns_false_if_disabled_moderation(self):
        PageModeration.objects.create(
            extended_object=self.pg1,
            disable_moderation=True
        )
        self.assertFalse(can_page_be_moderated(self.pg1))
