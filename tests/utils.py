from django.contrib.auth.models import User, Group
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
        cls.wf1 = Workflow.objects.create(pk=1, name='Workflow 1', is_default=True,)
        cls.wf2 = Workflow.objects.create(pk=2, name='Workflow 2',)
        cls.wf3 = Workflow.objects.create(pk=3, name='Workflow 3',)

        # create pages
        cls.pg1 = create_page(title='Page 1', template='page.html', language='en',)
        cls.pg2 = create_page(title='Page 2', template='page.html', language='en',)
        cls.pg3 = create_page(title='Page 3', template='page.html', language='en',)
        cls.pg4 = create_page(title='Page 4', template='page.html', language='en',)

        # create users, groups and roles
        cls.user = User.objects.create_superuser(username='test', email='test@test.com', password='test',)
        cls.user2 = User.objects.create_superuser(username='test2', email='test2@test.com', password='test2',)
        cls.user3 = User.objects.create_superuser(username='test3', email='test3@test.com', password='test3',)
        cls.group = Group.objects.create(name='Group 1',)
        cls.user2.groups.add(cls.group)
        cls.user3.groups.add(cls.group)

        cls.role1 = Role.objects.create(name='Role 1', user=cls.user,)
        cls.role2 = Role.objects.create(name='Role 2', user=cls.user2,)
        cls.role3 = Role.objects.create(name='Role 3', group=cls.group,)

        # create workflow steps for workflow
        cls.wf1st1 = cls.wf1.steps.create(role=cls.role1, is_required=True, order=1,)
        cls.wf1st2 = cls.wf1.steps.create(role=cls.role2, is_required=False, order=2,)
        cls.wf1st3 = cls.wf1.steps.create(role=cls.role3, is_required=True, order=3,)

        cls.wf2st1 = cls.wf2.steps.create(role=cls.role1, is_required=True, order=1,)
        cls.wf2st2 = cls.wf2.steps.create(role=cls.role3, is_required=True, order=2,)

        cls.wf3st1 = cls.wf3.steps.create(role=cls.role1, is_required=True, order=1,)
        cls.wf3st2 = cls.wf3.steps.create(role=cls.role3, is_required=False, order=2,)

        # create page moderation requests and actions
        cls.moderation_request1 = PageModerationRequest.objects.create(page=cls.pg1, language='en', workflow=cls.wf1, is_active=True,)
        cls.moderation_request1.actions.create(by_user=cls.user, action=constants.ACTION_STARTED,)

        PageModerationRequest.objects.create(page=cls.pg1, language='en', workflow=cls.wf1, is_active=False,)
        PageModerationRequest.objects.create(page=cls.pg2, language='en', workflow=cls.wf2, is_active=False,)

        cls.moderation_request2 = PageModerationRequest.objects.create(page=cls.pg3, language='en', workflow=cls.wf2, is_active=True,)
        cls.moderation_request2.actions.create(by_user=cls.user, action=constants.ACTION_STARTED,)
        cls.moderation_request2.actions.create(by_user=cls.user, action=constants.ACTION_APPROVED, step_approved=cls.wf2st1,)
        cls.moderation_request2.actions.create(by_user=cls.user, action=constants.ACTION_APPROVED, step_approved=cls.wf2st2,)

        cls.moderation_request3 = PageModerationRequest.objects.create(page=cls.pg4, language='en', workflow=cls.wf3, is_active=True,)
        cls.moderation_request3.actions.create(by_user=cls.user, action=constants.ACTION_STARTED,)
        cls.moderation_request3.actions.create(by_user=cls.user, to_user=cls.user2, action=constants.ACTION_APPROVED, step_approved=cls.wf3st1,)


class BaseViewTestCase(BaseTestCase):

    def setUp(self):
        self.client.force_login(self.user)
