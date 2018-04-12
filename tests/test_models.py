import re
from unittest.mock import MagicMock, patch

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings

from cms.api import create_page

from djangocms_moderation.models import *
from djangocms_moderation import constants
from djangocms_moderation.emails import notify_requested_moderator

from .utils import BaseTestCase


class RoleTest(BaseTestCase):

    def test_user_and_group_validation_error(self):
        role = Role.objects.create(name='New Role 1', user=self.user, group=self.group)
        self.assertRaisesMessage(ValidationError, 'Can\'t pick both user and group. Only one.', role.clean)

    def test_user_is_assigned(self):
        # with user
        role = Role.objects.create(name='New Role 1', user=self.user)
        self.assertTrue(role.user_is_assigned(self.user))
        self.assertFalse(role.user_is_assigned(self.user2))
        # with group
        role = Role.objects.create(name='New Role 2', group=self.group)
        self.assertFalse(role.user_is_assigned(self.user))
        self.assertTrue(role.user_is_assigned(self.user2))

    def test_get_users_queryset(self):
        # with user
        role = Role.objects.create(name='New Role 1', user=self.user)
        self.assertQuerysetEqual(role.get_users_queryset(), User.objects.filter(pk=self.user.pk), transform=lambda x: x, ordered=False)
        # with group
        role = Role.objects.create(name='New Role 2', group=self.group)
        self.assertQuerysetEqual(role.get_users_queryset(), User.objects.filter(pk__in=[self.user2.pk, self.user3.pk]), transform=lambda x: x, ordered=False)


class WorkflowTest(BaseTestCase):

    def test_non_unique_reference_number_prefix_validation_error(self):
        workflow = Workflow.objects.create(name='New Workflow 1', is_default=False, is_reference_number_required=True, reference_number_prefix='')
        workflow.clean()
        workflow = Workflow.objects.create(name='New Workflow 2', is_default=False, is_reference_number_required=False, reference_number_prefix='')
        workflow.clean()
        workflow = Workflow.objects.create(name='New Workflow 3', is_default=False, is_reference_number_required=True, reference_number_prefix='NW3')
        workflow.clean()
        workflow = Workflow.objects.create(name='New Workflow 4', is_default=False, is_reference_number_required=True, reference_number_prefix='NW3')
        self.assertRaisesMessage(ValidationError, 'The reference number prefix entered is already in use by another workflows.', workflow.clean)

    def test_multiple_defaults_validation_error(self):
        workflow = Workflow.objects.create(name='New Workflow 3', is_default=False)
        workflow.clean()
        workflow = Workflow.objects.create(name='New Workflow 4', is_default=True) # self.wf1 is default
        self.assertRaisesMessage(ValidationError, 'Can\'t have two default workflows, only one is allowed.', workflow.clean)

    def test_first_step(self):
        self.assertEqual(self.wf1.first_step, self.wf1st1)

    @patch('djangocms_moderation.models.notify_requested_moderator')
    def test_submit_new_request(self, mock_nrm):
        request = self.wf1.submit_new_request(
            by_user=self.user,
            page=self.pg3,
            language='en',
            message='Some message'
        )
        self.assertQuerysetEqual(request.actions.all(), PageModerationRequestAction.objects.filter(request=request), transform=lambda x: x, ordered=False)
        mock_nrm.assert_called_once()


class WorkflowStepTest(BaseTestCase):

    def test_get_next(self):
        self.assertEqual(self.wf1st1.get_next(), self.wf1st2)
        self.assertEqual(self.wf1st2.get_next(), self.wf1st3)
        self.assertIsNone(self.wf1st3.get_next())

    def test_get_next_required(self):
        self.assertEqual(self.wf1st1.get_next_required(), self.wf1st3)
        self.assertEqual(self.wf1st2.get_next_required(), self.wf1st3)
        self.assertIsNone(self.wf1st3.get_next_required())


class PageModerationRequestTest(BaseTestCase):

    def test_has_pending_step(self):
        self.assertTrue(self.moderation_request1.has_pending_step)
        self.assertFalse(self.moderation_request2.has_pending_step)
        self.assertTrue(self.moderation_request3.has_pending_step)

    def test_required_pending_steps(self):
        self.assertTrue(self.moderation_request1.has_required_pending_steps)
        self.assertFalse(self.moderation_request2.has_required_pending_steps)
        self.assertFalse(self.moderation_request3.has_required_pending_steps)

    def test_is_approved(self):
        self.assertFalse(self.moderation_request1.is_approved)
        self.assertTrue(self.moderation_request2.is_approved)
        self.assertTrue(self.moderation_request3.is_approved)

    def test_get_first_action(self):
        self.assertEqual(self.moderation_request2.get_first_action(), self.moderation_request2.actions.first())

    def test_get_last_action(self):
        self.assertEqual(self.moderation_request2.get_last_action(), self.moderation_request2.actions.last())

    def test_get_pending_steps(self):
        self.assertQuerysetEqual(self.moderation_request3.get_pending_steps(), WorkflowStep.objects.filter(pk__in=[self.wf3st2.pk]), transform=lambda x: x, ordered=False)

    def test_get_pending_required_steps(self):
        self.assertQuerysetEqual(self.moderation_request1.get_pending_required_steps(), WorkflowStep.objects.filter(pk__in=[self.wf1st1.pk, self.wf1st3.pk]), transform=lambda x: x, ordered=False)
        self.assertQuerysetEqual(self.moderation_request3.get_pending_required_steps(), WorkflowStep.objects.none(), transform=lambda x: x, ordered=False)

    def test_get_next_required(self):
        self.assertEqual(self.moderation_request1.get_next_required(), self.wf1st1)
        self.assertIsNone(self.moderation_request3.get_next_required())

    def test_user_get_step(self):
        self.assertIsNone(self.moderation_request3.user_get_step(self.user))
        self.assertEqual(self.moderation_request3.user_get_step(self.user2), self.wf3st2)

    def test_user_can_take_action(self):
        temp_user = User.objects.create_superuser(username='temp', email='temp@temp.com', password='temp')
        self.assertFalse(self.moderation_request1.user_can_take_action(temp_user))
        self.assertFalse(self.moderation_request3.user_can_take_action(self.user))
        self.assertTrue(self.moderation_request3.user_can_take_action(self.user2))

    @patch('djangocms_moderation.models.notify_request_author')
    @patch('djangocms_moderation.models.notify_requested_moderator')
    def test_update_status_action_approved(self, mock_nrm, mock_nra):
        self.moderation_request1.update_status(
            action=constants.ACTION_APPROVED,
            by_user=self.user,
            message='Approved'
        )
        self.assertTrue(self.moderation_request1.is_active)
        self.assertEqual(len(self.moderation_request1.actions.all()), 2)
        mock_nrm.assert_called_once()
        mock_nra.assert_called_once()

    @patch('djangocms_moderation.models.notify_request_author')
    @patch('djangocms_moderation.models.notify_requested_moderator')
    def test_update_status_action_rejected(self, mock_nrm, mock_nra):
        self.moderation_request1.update_status(
            action=constants.ACTION_REJECTED,
            by_user=self.user,
            message='Rejected'
        )
        self.assertFalse(self.moderation_request1.is_active)
        self.assertEqual(len(self.moderation_request1.actions.all()), 2)

    @patch('djangocms_moderation.models.PageModerationRequest.getTimeStamp', return_value=1234567890.123123)
    def test_reference_number_with_prefix(self, mock_get_timestamp):
        request = PageModerationRequest.objects.create(
            page=self.pg1,
            language='en',
            is_active=True,
            workflow=self.wf2
        )
        mock_get_timestamp.assert_called_once()
        self.assertEqual(request.reference_number, '{}{}'.format(self.wf2.reference_number_prefix, mock_get_timestamp()))

    @patch('djangocms_moderation.models.PageModerationRequest.getTimeStamp', return_value=2345678901.123123)
    def test_reference_number_without_prefix(self, mock_get_timestamp):
        request = PageModerationRequest.objects.create(
            page=self.pg1,
            language='en',
            is_active=True,
            workflow=self.wf1
        )
        mock_get_timestamp.assert_called_once()
        self.assertEqual(request.reference_number, '{}'.format(mock_get_timestamp()))


class PageModerationRequestActionTest(BaseTestCase):

    def test_get_by_user_name(self):
        action = self.moderation_request3.actions.last()
        self.assertEqual(action.get_by_user_name(), self.user.username)

    def test_get_to_user_name(self):
        action = self.moderation_request3.actions.last()
        self.assertEqual(action.get_to_user_name(), self.user2.username)
        action = self.moderation_request1.actions.last()
        self.assertIsNone(action.get_to_user_name())

    def test_save_when_to_user_passed(self):
        new_action = self.moderation_request1.actions.create(by_user=self.user, to_user=self.user2, action=constants.ACTION_APPROVED, step_approved=self.wf1st1)
        self.assertEqual(new_action.to_role, self.role2)

    def test_save_when_to_user_not_passed_and_action_started(self):
        new_request = PageModerationRequest.objects.create(page=self.pg2, language='en', workflow=self.wf1, is_active=True)
        new_action = new_request.actions.create(by_user=self.user, action=constants.ACTION_STARTED)
        self.assertEqual(new_action.to_role, self.role1)

    def test_save_when_to_user_not_passed_and_action_not_started(self):
        new_action = self.moderation_request1.actions.create(by_user=self.user, action=constants.ACTION_APPROVED, step_approved=self.wf1st1)
        self.assertEqual(new_action.to_role, self.role2)
