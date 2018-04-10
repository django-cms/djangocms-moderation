from unittest.mock import MagicMock, patch

from django.contrib.auth.models import User, Group
from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings

from cms.api import create_page

from djangocms_moderation.models import *
from djangocms_moderation import constants
from djangocms_moderation.emails import notify_requested_moderator
import re

class WorkflowTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        # create workflows
        cls.wf1 = Workflow.objects.create(pk=1, name='Workflow 1', is_default=True, is_reference_number_required=True, reference_number_prefix="")
        cls.wf2 = Workflow.objects.create(pk=2, name='Workflow 2', is_default=False, is_reference_number_required=True, reference_number_prefix="TST")
        # create pages
        cls.pg1 = create_page(title='Page 1', template='page.html', language='en')
        cls.pg2 = create_page(title='Page 2', template='page.html', language='en')
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

    def test_submit_new_request(self):
        # test that when a workflow submits a new request, the ModerationRequest gets a reference number generated correctly
        print(len(PageModerationRequest.objects.all()))
        request = self.wf1.submit_new_request(
            by_user=self.user,
            page=self.pg1,
            language='en'
        )
        self.assertTrue(len(PageModerationRequest.objects.all()) == 1)
        search = re.search(r'[0-9.]',PageModerationRequest.objects.all()[0].reference_number)
        self.assertEqual(search.start(), 0)

        # check for reference number prefix
        request = self.wf2.submit_new_request(
            by_user=self.user,
            page=self.pg2,
            language='en'
        )
        search = re.search(r'[0-9.]',PageModerationRequest.objects.all()[1].reference_number)
        self.assertEqual(search.start(), 3)

class RoleTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username='test', email='test@test.com', password='test', is_staff=True, is_superuser=True)
        cls.user2 = User.objects.create_user(username='test2', email='test2@test.com', password='test2', is_staff=True, is_superuser=True)
        cls.group = Group.objects.create(name='Group 1')
        cls.group2 = Group.objects.create(name='Group 2')
        cls.user.groups.add(cls.group)
        cls.user2.groups.add(cls.group2)

    def test_create_role(self):
        role = Role.objects.create(
            name='Role 1',
            user=self.user
        )
        self.assertEqual(role, Role.objects.get(name='Role 1'))

    def test_user_and_group_validation_error(self):
        role = Role.objects.create(
            name='Role 1',
            user=self.user,
            group=self.group
        )
        self.assertRaisesMessage(ValidationError, 'Can\'t pick both user and group. Only one.', role.clean)

    def test_user_is_assigned(self):
        # with user
        role = Role.objects.create(
            name='Role 1',
            user=self.user
        )
        self.assertTrue(role.user_is_assigned(self.user))
        self.assertFalse(role.user_is_assigned(self.user2))
        # with group
        role = Role.objects.create(
            name='Role 2',
            group=self.group2
        )
        self.assertTrue(role.user_is_assigned(self.user2))
        self.assertFalse(role.user_is_assigned(self.user))

    def test_get_users_queryset(self):
        # with user
        role = Role.objects.create(
            name='Role 1',
            user=self.user
        )
        self.assertQuerysetEqual(role.get_users_queryset(), User.objects.filter(pk=self.user.pk), transform=lambda x: x, ordered=False)
        # with group
        role = Role.objects.create(
            name='Role 2',
            group=self.group2
        )
        self.assertQuerysetEqual(role.get_users_queryset(), User.objects.filter(pk=self.user2.pk), transform=lambda x: x, ordered=False)
