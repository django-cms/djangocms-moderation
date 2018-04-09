from django.test import TestCase, override_settings

from djangocms_moderation.helpers import *
from djangocms_moderation.models import Workflow

from .utils import BaseTestCase


class GetWorkflowByIdTest(BaseTestCase):

    def test_existing_workflow(self):
        workflow = Workflow.objects.get(pk=1)
        self.assertEqual(get_workflow_by_id(1), workflow)
        workflow = Workflow.objects.get(pk=2)
        self.assertEqual(get_workflow_by_id(2), workflow)

    def test_non_existing_workflow(self):
        self.assertEqual(get_workflow_by_id(3), None)


class GetCurrentModerationRequestTest(BaseTestCase):

    def test_existing_moderation_request(self):
        active_request = get_current_moderation_request(self.pg1, 'en')
        self.assertEqual(active_request, self.moderation_request1)

    def test_no_moderation_request(self):
        active_request = get_current_moderation_request(self.pg2, 'en')
        self.assertEqual(active_request, None)


class GetPageTest(BaseTestCase):

    def test_returns_page(self):
        self.assertEqual(get_page(self.pg1.pk, 'en'), self.pg1)
