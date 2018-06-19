import json
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.urlresolvers import reverse

from cms.api import create_page

from djangocms_moderation import constants
from djangocms_moderation.models import (
    ConfirmationFormSubmission,
    ConfirmationPage,
    PageModerationRequest,
    PageModerationRequestAction,
    Role,
    Workflow,
    WorkflowStep,
)

from .utils import BaseTestCase


class RoleTest(BaseTestCase):

    def test_user_and_group_validation_error(self):
        role = Role.objects.create(name='New Role 1', user=self.user, group=self.group,)
        self.assertRaisesMessage(ValidationError, 'Can\'t pick both user and group. Only one.', role.clean)

    def test_user_is_assigned(self):
        # with user
        role = Role.objects.create(name='New Role 1', user=self.user,)
        self.assertTrue(role.user_is_assigned(self.user))
        self.assertFalse(role.user_is_assigned(self.user2))
        # with group
        role = Role.objects.create(name='New Role 2', group=self.group,)
        self.assertFalse(role.user_is_assigned(self.user))
        self.assertTrue(role.user_is_assigned(self.user2))

    def test_get_users_queryset(self):
        # with user
        role = Role.objects.create(name='New Role 1', user=self.user,)
        self.assertQuerysetEqual(
            role.get_users_queryset(), User.objects.filter(pk=self.user.pk), transform=lambda x: x, ordered=False)
        # with group
        role = Role.objects.create(name='New Role 2', group=self.group,)
        self.assertQuerysetEqual(
            role.get_users_queryset(), User.objects.filter(
                pk__in=[self.user2.pk, self.user3.pk]
            ), transform=lambda x: x, ordered=False
        )


class WorkflowTest(BaseTestCase):

    def test_multiple_defaults_validation_error(self):
        workflow = Workflow.objects.create(name='New Workflow 3', is_default=False,)
        workflow.clean()
        workflow = Workflow.objects.create(name='New Workflow 4', is_default=True,)  # self.wf1 is default
        self.assertRaisesMessage(
            ValidationError, 'Can\'t have two default workflows, only one is allowed.', workflow.clean
        )

    def test_first_step(self):
        self.assertEqual(self.wf1.first_step, self.wf1st1)

    @patch('djangocms_moderation.models.notify_requested_moderator')
    def test_submit_new_request(self, mock_nrm):
        request = self.wf1.submit_new_request(
            by_user=self.user,
            page=self.pg3,
            language='en',
            message='Some message',
        )
        self.assertQuerysetEqual(
            request.actions.all(),
            PageModerationRequestAction.objects.filter(request=request),
            transform=lambda x: x,
            ordered=False,
        )
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
        self.assertEqual(
            self.moderation_request2.get_first_action(),
            self.moderation_request2.actions.first()
        )

    def test_get_author(self):
        self.assertEqual(
            self.user,
            self.moderation_request2.author
        )
        del self.moderation_request2.author  # Invalidate cached_property

        # Lets change the first step's by_user, which should become our
        # new author
        first_action = self.moderation_request2.get_first_action()
        first_action.by_user = self.user2
        first_action.save()

        self.assertEqual(
            self.user2,
            self.moderation_request2.author
        )

    def test_get_last_action(self):
        self.assertEqual(
            self.moderation_request2.get_last_action(),
            self.moderation_request2.actions.last()
        )

    def test_get_pending_steps(self):
        self.assertQuerysetEqual(
            self.moderation_request3.get_pending_steps(),
            WorkflowStep.objects.filter(pk__in=[self.wf3st2.pk]),
            transform=lambda x: x,
            ordered=False,
        )

        # Now lets make the Approve action for wf3st1 stale...
        last_action = self.moderation_request3.get_last_action()
        last_action.is_stale = True
        last_action.save()

        # ... so all the steps are now pending as we need to re-moderate the
        # resubmitted request
        self.assertQuerysetEqual(
            self.moderation_request3.get_pending_steps(),
            WorkflowStep.objects.filter(workflow=self.wf3),
            transform=lambda x: x,
            ordered=False,
        )

    def test_get_pending_required_steps(self):
        self.assertQuerysetEqual(
            self.moderation_request1.get_pending_required_steps(),
            WorkflowStep.objects.filter(pk__in=[self.wf1st1.pk, self.wf1st3.pk]),
            transform=lambda x: x,
            ordered=False,
        )
        self.assertQuerysetEqual(
            self.moderation_request3.get_pending_required_steps(),
            WorkflowStep.objects.none(),
            transform=lambda x: x,
            ordered=False,
        )

        # Lets test with stale action
        self.assertQuerysetEqual(
            self.moderation_request2.get_pending_required_steps(),
            WorkflowStep.objects.none(),
            transform=lambda x: x,
            ordered=False,
        )

        # Make the last action stale
        last_action = self.moderation_request2.get_last_action()
        last_action.is_stale = True
        last_action.save()

        self.assertQuerysetEqual(
            self.moderation_request2.get_pending_required_steps(),
            WorkflowStep.objects.filter(pk=last_action.step_approved.pk),
            transform=lambda x: x,
            ordered=False,
        )

    def test_get_next_required(self):
        self.assertEqual(self.moderation_request1.get_next_required(), self.wf1st1)
        self.assertIsNone(self.moderation_request3.get_next_required())

    def test_user_get_step(self):
        self.assertIsNone(self.moderation_request3.user_get_step(self.user))
        self.assertEqual(self.moderation_request3.user_get_step(self.user2), self.wf3st2)

    def test_user_can_take_moderation_action(self):
        temp_user = User.objects.create_superuser(username='temp', email='temp@temp.com', password='temp',)
        self.assertFalse(self.moderation_request1.user_can_take_moderation_action(temp_user))
        self.assertFalse(self.moderation_request3.user_can_take_moderation_action(self.user))
        self.assertTrue(self.moderation_request3.user_can_take_moderation_action(self.user2))

    def test_user_can_edit_and_resubmit(self):
        temp_user = User.objects.create_superuser(username='temp', email='temp@temp.com', password='temp',)
        self.assertFalse(self.moderation_request1.user_can_edit_and_resubmit(temp_user))

        author = self.moderation_request3.author
        last_action = self.moderation_request3.get_last_action()
        last_action.action = constants.ACTION_REJECTED
        last_action.save()
        # Only author can edit and resubmit
        self.assertTrue(self.moderation_request3.user_can_edit_and_resubmit(author))
        self.assertFalse(self.moderation_request3.user_can_edit_and_resubmit(self.user2))
        self.assertFalse(self.moderation_request3.user_can_edit_and_resubmit(self.user3))

    def test_user_can_moderate(self):
        temp_user = User.objects.create_superuser(username='temp', email='temp@temp.com', password='temp',)
        self.assertFalse(self.moderation_request1.user_can_moderate(temp_user))
        self.assertFalse(self.moderation_request2.user_can_moderate(temp_user))
        self.assertFalse(self.moderation_request3.user_can_moderate(temp_user))

        # check that it doesn't allow access to users that aren't part of this moderation request
        self.pg5 = create_page(title='Page 5', template='page.html', language='en',)
        self.user4 = User.objects.create_superuser(username='test4', email='test4@test.com', password='test4',)
        self.role4 = Role.objects.create(name='Role 4', user=self.user4,)
        self.wf4 = Workflow.objects.create(pk=4, name='Workflow 4',)
        self.wf4st1 = self.wf4.steps.create(role=self.role4, is_required=True, order=1,)
        self.wf4st2 = self.wf4.steps.create(role=self.role1, is_required=False, order=2,)
        self.moderation_request4 = PageModerationRequest.objects.create(
            page=self.pg5, language='en', workflow=self.wf4, is_active=True,)
        self.moderation_request4.actions.create(by_user=self.user, action=constants.ACTION_STARTED,)

        self.assertTrue(self.moderation_request4.user_can_moderate(self.user))
        self.assertFalse(self.moderation_request4.user_can_moderate(self.user2))
        self.assertFalse(self.moderation_request4.user_can_moderate(self.user3))
        self.assertTrue(self.moderation_request4.user_can_moderate(self.user4))

    @patch('djangocms_moderation.models.notify_request_author')
    @patch('djangocms_moderation.models.notify_requested_moderator')
    def test_update_status_action_approved(self, mock_nrm, mock_nra):
        self.moderation_request1.update_status(
            action=constants.ACTION_APPROVED,
            by_user=self.user,
            message='Approved',
        )
        self.assertTrue(self.moderation_request1.is_active)
        self.assertEqual(len(self.moderation_request1.actions.filter(is_stale=False)), 2)
        mock_nrm.assert_called_once()
        mock_nra.assert_called_once()

    @patch('djangocms_moderation.models.notify_request_author')
    @patch('djangocms_moderation.models.notify_requested_moderator')
    def test_update_status_action_rejected(self, mock_nrm, mock_nra):
        self.moderation_request1.update_status(
            action=constants.ACTION_REJECTED,
            by_user=self.user,
            message='Rejected',
        )
        self.assertTrue(self.moderation_request1.is_active)
        self.assertEqual(len(self.moderation_request1.actions.all()), 2)

        mock_nra.assert_called_once()
        # No need to notify the moderator, as this is assigned back to the
        # content author
        self.assertFalse(mock_nrm.called)

    @patch('djangocms_moderation.models.notify_request_author')
    @patch('djangocms_moderation.models.notify_requested_moderator')
    def test_update_status_action_resubmitted(self, mock_nrm, mock_nra):
        self.moderation_request1.update_status(
            action=constants.ACTION_RESUBMITTED,
            by_user=self.user,
            message='Resubmitting',
        )
        self.assertTrue(self.moderation_request1.is_active)
        self.assertEqual(len(self.moderation_request1.actions.all()), 2)

        mock_nra.assert_called_once()
        mock_nrm.assert_called_once()

    def test_rejection_makes_the_previous_actions_stale(self):
        previous_action_1 = self.moderation_request1.actions.create(
            by_user=self.user,
            action=constants.ACTION_APPROVED,
        )
        previous_action_2 = self.moderation_request1.actions.create(
            by_user=self.user2,
            action=constants.ACTION_RESUBMITTED,
        )

        self.assertFalse(previous_action_1.is_stale)
        self.assertFalse(previous_action_2.is_stale)

        self.moderation_request1.update_status(
            action=constants.ACTION_REJECTED,
            by_user=self.user,
            message='Rejecting this',
        )

        previous_action_1.refresh_from_db()
        previous_action_2.refresh_from_db()
        self.assertTrue(previous_action_1.is_stale)
        self.assertTrue(previous_action_2.is_stale)

    @patch('djangocms_moderation.models.generate_reference_number')
    def test_reference_number(self, mock_uuid):
        mock_uuid.return_value = 'abc123'

        request = PageModerationRequest.objects.create(
            page=self.pg1,
            language='en',
            is_active=True,
            workflow=self.wf1,
        )
        mock_uuid.assert_called_once()
        self.assertEqual(request.reference_number, 'abc123')


class PageModerationRequestActionTest(BaseTestCase):

    def test_get_by_user_name(self):
        action = self.moderation_request3.actions.last()
        self.assertEqual(action.get_by_user_name(), self.user.username)

    def test_get_to_user_name(self):
        action = self.moderation_request3.actions.last()
        self.assertEqual(action.get_to_user_name(), self.user2.username)

    def test_save_when_to_user_passed(self):
        new_action = self.moderation_request1.actions.create(
            by_user=self.user,
            to_user=self.user2,
            action=constants.ACTION_APPROVED,
            step_approved=self.wf1st1,
        )
        self.assertEqual(new_action.to_role, self.role2)

    def test_save_when_to_user_not_passed_and_action_started(self):
        new_request = PageModerationRequest.objects.create(
            page=self.pg2,
            language='en',
            workflow=self.wf1,
            is_active=True,
        )
        new_action = new_request.actions.create(by_user=self.user, action=constants.ACTION_STARTED,)
        self.assertEqual(new_action.to_role, self.role1)

    def test_save_when_to_user_not_passed_and_action_not_started(self):
        new_action = self.moderation_request1.actions.create(
            by_user=self.user,
            action=constants.ACTION_APPROVED,
            step_approved=self.wf1st1,
        )
        self.assertEqual(new_action.to_role, self.role2)


class ConfirmationPageTest(BaseTestCase):

    def setUp(self):
        # First delete all the form submissions for the moderation_request1
        # This will make sure there are no form submissions
        # attached with the self.moderation_request1
        self.moderation_request1.form_submissions.all().delete()
        self.cp = ConfirmationPage.objects.create(
            name='Checklist Form',
        )
        self.role1.confirmation_page = self.cp
        self.role1.save()

    def test_get_absolute_url(self):
        url = reverse('admin:cms_moderation_confirmation_page', args=(self.cp.pk,))
        self.assertEqual(self.cp.get_absolute_url(), url)

    def test_is_valid_returns_false_when_no_form_submission(self):
        result = self.cp.is_valid(active_request=self.moderation_request1, for_step=self.wf1st1,)
        self.assertFalse(result)

    def test_is_valid_returns_true_when_form_submission_exists(self):
        cfs = ConfirmationFormSubmission.objects.create(
            request=self.moderation_request1,
            for_step=self.wf1st1,
            by_user=self.user,
            data=json.dumps([{'label': 'Question 1', 'answer': 'Yes'}]),
            confirmation_page=self.cp,
        )
        result = self.cp.is_valid(active_request=self.moderation_request1, for_step=self.wf1st1,)
        self.assertTrue(result)

    def test_is_valid_returns_false_when_plain_content_not_reviewed(self):
        result = self.cp.is_valid(active_request=self.moderation_request1, for_step=self.wf1st1,)
        self.assertFalse(result)


class ConfirmationFormSubmissionTest(BaseTestCase):

    def setUp(self):
        self.cp = ConfirmationPage.objects.create(
            name='Checklist Form',
        )
        self.role1.confirmation_page = self.cp
        self.role1.save()

    def test_get_by_user_name(self):
        cfs = ConfirmationFormSubmission.objects.create(
            request=self.moderation_request1,
            for_step=self.wf1st1,
            by_user=self.user,
            data=json.dumps([{'label': 'Question 1', 'answer': 'Yes'}]),
            confirmation_page=self.cp,
        )
        self.assertEqual(cfs.get_by_user_name(), self.user.username)
