from django.contrib.auth.models import User
from django.test import TestCase
from django.utils.translation import override as force_language

from cms.api import create_page
from cms.utils.urlutils import admin_reverse

from djangocms_moderation.models import *
from djangocms_moderation import constants


class BaseTestCase(TestCase):

    @classmethod
    def setUpTestData(cls):
        # create workflows
        cls.wf1 = Workflow.objects.create(pk=1, name='Workflow 1', is_default=True, is_reference_number_required=True, reference_number_prefix="")
        cls.wf2 = Workflow.objects.create(pk=2, name='Workflow 2')

        # create pages
        cls.pg1 = create_page(title='Page 1', template='page.html', language='en')
        cls.pg2 = create_page(title='Page 2', template='page.html', language='en')
        cls.pg3 = create_page(title='Page 3', template='page.html', language='en')

        # create roles
        cls.user = User.objects.create_user(username='test', email='test@test.com', password='test', is_staff=True, is_superuser=True)
        cls.role1 = Role.objects.create(name='Role 1', user=cls.user)
        cls.role2 = Role.objects.create(name='Role 2', user=cls.user)
        cls.role3 = Role.objects.create(name='Role 3', user=cls.user)

        # create workflow steps for workflow
        WorkflowStep.objects.create(role=cls.role1, is_required=True, workflow=cls.wf1, order=1)
        WorkflowStep.objects.create(role=cls.role2, is_required=True, workflow=cls.wf1, order=2)
        WorkflowStep.objects.create(role=cls.role3, is_required=True, workflow=cls.wf1, order=3)

        WorkflowStep.objects.create(role=cls.role1, is_required=True, workflow=cls.wf2, order=1)
        WorkflowStep.objects.create(role=cls.role3, is_required=True, workflow=cls.wf2, order=2)

        # create page moderation request and action
        cls.moderation_request1 = PageModerationRequest.objects.create(page=cls.pg1, language='en', workflow=cls.wf1, is_active=True, reference_number="00000000000001")
        cls.moderation_request1.actions.create(by_user=cls.user, to_user=cls.user, action=constants.ACTION_STARTED)

        PageModerationRequest.objects.create(page=cls.pg1, language='en', workflow=cls.wf1, is_active=False, reference_number="00000000000002")
        PageModerationRequest.objects.create(page=cls.pg2, language='en', workflow=cls.wf2, is_active=False, reference_number="00000000000003")

        cls.moderation_request2 = PageModerationRequest.objects.create(page=cls.pg3, language='en', workflow=cls.wf2, is_active=True, reference_number="00000000000004")
        cls.moderation_request2.actions.create(by_user=cls.user, to_user=cls.user, action=constants.ACTION_STARTED)
        cls.moderation_request2.actions.create(by_user=cls.user, to_user=cls.user, action=constants.ACTION_APPROVED, step_approved=WorkflowStep.objects.get(workflow=cls.wf2, order=1))
        cls.moderation_request2.actions.create(by_user=cls.user, to_user=cls.user, action=constants.ACTION_APPROVED, step_approved=WorkflowStep.objects.get(workflow=cls.wf2, order=2))


class BaseViewTestCase(BaseTestCase):

    def setUp(self):
        self.client.force_login(self.user)


def get_admin_url(name, language, args):
    with force_language(language):
        return admin_reverse(name, args=args)
