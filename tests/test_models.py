import json
from mock import patch
from unittest import skip

from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.core.urlresolvers import reverse

from cms.api import create_page

from djangocms_moderation import constants
from djangocms_moderation.exceptions import ObjectAlreadyInCollection, ObjectNotInCollection
from djangocms_moderation.models import (
    ConfirmationFormSubmission,
    ConfirmationPage,
    ModerationCollection,
    ModerationRequest,
    ModerationRequestAction,
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

    @skip('4.0 rework TBC')
    @patch('djangocms_moderation.models.notify_requested_moderator')
    def test_submit_new_request(self, mock_nrm):
        request = self.wf1.submit_new_request(
            by_user=self.user,
            obj=self.pg3,
            language='en',
            message='Some message',
        )
        self.assertQuerysetEqual(
            request.actions.all(),
            ModerationRequestAction.objects.filter(request=request),
            transform=lambda x: x,
            ordered=False,
        )
        self.assertEqual(mock_nrm.call_count, 1)


class WorkflowStepTest(BaseTestCase):

    def test_get_next(self):
        self.assertEqual(self.wf1st1.get_next(), self.wf1st2)
        self.assertEqual(self.wf1st2.get_next(), self.wf1st3)
        self.assertIsNone(self.wf1st3.get_next())

    def test_get_next_required(self):
        self.assertEqual(self.wf1st1.get_next_required(), self.wf1st3)
        self.assertEqual(self.wf1st2.get_next_required(), self.wf1st3)
        self.assertIsNone(self.wf1st3.get_next_required())


class ModerationRequestTest(BaseTestCase):

    def test_has_pending_step(self):
        self.assertTrue(self.moderation_request1.has_pending_step())
        self.assertFalse(self.moderation_request2.has_pending_step())
        self.assertTrue(self.moderation_request3.has_pending_step())

    def test_required_pending_steps(self):
        self.assertTrue(self.moderation_request1.has_required_pending_steps())
        self.assertFalse(self.moderation_request2.has_required_pending_steps())
        self.assertFalse(self.moderation_request3.has_required_pending_steps())

    def test_is_approved(self):
        self.assertFalse(self.moderation_request1.is_approved())
        self.assertTrue(self.moderation_request2.is_approved())
        self.assertTrue(self.moderation_request3.is_approved())

    def test_is_rejected(self):
        self.assertFalse(self.moderation_request1.is_rejected())
        self.assertFalse(self.moderation_request2.is_rejected())
        self.assertTrue(self.moderation_request4.is_rejected())

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

        # Now lets make the Approve action for wf3st1 archived...
        last_action = self.moderation_request3.get_last_action()
        last_action.is_archived = True
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

        # Lets test with archived action
        self.assertQuerysetEqual(
            self.moderation_request2.get_pending_required_steps(),
            WorkflowStep.objects.none(),
            transform=lambda x: x,
            ordered=False,
        )

        # Make the last action archived
        last_action = self.moderation_request2.get_last_action()
        last_action.is_archived = True
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

    def test_user_can_resubmit(self):
        temp_user = User.objects.create_superuser(username='temp', email='temp@temp.com', password='temp',)
        self.assertFalse(self.moderation_request1.user_can_resubmit(temp_user))
        author = self.moderation_request4.author
        # Only author can edit and resubmit
        self.assertTrue(self.moderation_request4.user_can_resubmit(author))
        self.assertFalse(self.moderation_request4.user_can_resubmit(self.user2))
        self.assertFalse(self.moderation_request4.user_can_resubmit(self.user3))

    def test_user_is_author(self):
        temp_user = User.objects.create_superuser(username='temp', email='temp@temp.com', password='temp',)
        self.assertFalse(self.moderation_request1.user_is_author(temp_user))
        self.assertFalse(self.moderation_request1.user_is_author(self.user2))
        self.assertTrue(self.moderation_request1.user_is_author(self.user))

    def test_user_can_view_comments(self):
        temp_user = User.objects.create_superuser(username='temp', email='temp@temp.com', password='temp',)
        self.assertFalse(self.moderation_request1.user_can_view_comments(temp_user))
        self.assertTrue(self.moderation_request1.user_can_view_comments(self.user2))
        self.assertTrue(self.moderation_request1.user_can_view_comments(self.user))

    def test_user_can_moderate(self):
        temp_user = User.objects.create_superuser(username='temp', email='temp@temp.com', password='temp',)
        self.assertFalse(self.moderation_request1.user_can_moderate(temp_user))
        self.assertFalse(self.moderation_request2.user_can_moderate(temp_user))
        self.assertFalse(self.moderation_request3.user_can_moderate(temp_user))

        # check that it doesn't allow access to users that aren't part of this moderation request
        user4 = User.objects.create_superuser(username='test4', email='test4@test.com', password='test4',)
        self.assertTrue(self.moderation_request4.user_can_moderate(self.user))
        self.assertTrue(self.moderation_request4.user_can_moderate(self.user2))
        self.assertTrue(self.moderation_request4.user_can_moderate(self.user3))
        self.assertFalse(self.moderation_request4.user_can_moderate(user4))

    @patch('djangocms_moderation.models.notify_request_author')
    @patch('djangocms_moderation.models.notify_requested_moderator')
    def test_update_status_action_approved(self, mock_nrm, mock_nra):
        self.moderation_request1.update_status(
            action=constants.ACTION_APPROVED,
            by_user=self.user,
            message='Approved',
        )
        self.assertTrue(self.moderation_request1.is_active)
        self.assertEqual(len(self.moderation_request1.actions.filter(is_archived=False)), 2)
        self.assertEqual(mock_nrm.call_count, 1)
        self.assertEqual(mock_nra.call_count, 1)

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

        self.assertEqual(mock_nra.call_count, 1)
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

        self.assertEqual(mock_nra.call_count, 1)
        self.assertEqual(mock_nrm.call_count, 1)

    def test_compliance_number_is_generated(self):
        self.wf1.requires_compliance_number = True
        self.assertTrue(self.moderation_request1.has_required_pending_steps())
        self.moderation_request1.update_status(
            action=constants.ACTION_APPROVED, by_user=self.user
        )
        self.moderation_request1.refresh_from_db()
        self.assertFalse(self.moderation_request1.is_approved())
        # Compliance number is not yet generated as there are more approvers
        # to follow this one
        self.assertIsNone(self.moderation_request1.compliance_number)

        self.moderation_request1.update_status(
            action=constants.ACTION_APPROVED, by_user=self.user3
        )
        self.moderation_request1.refresh_from_db()
        self.assertTrue(self.moderation_request1.is_approved())
        # Now the moderation request is approved, so the compliance should
        # be generated
        self.assertIsNotNone(self.moderation_request1.compliance_number)

    def test_should_set_compliance_number(self):
        # `Workflow.requires_compliance_number` is False by default
        self.assertFalse(self.moderation_request1.should_set_compliance_number())
        self.assertFalse(self.moderation_request2.should_set_compliance_number())
        self.assertFalse(self.moderation_request3.should_set_compliance_number())

        # Lets enable compliance number
        self.wf1.requires_compliance_number = True
        self.wf2.requires_compliance_number = True
        self.wf3.requires_compliance_number = True

        # Now, request2 and request3 should allow the generation.
        # request1 is not approved yet, so it shouldn't
        self.assertFalse(self.moderation_request1.should_set_compliance_number())
        self.assertTrue(self.moderation_request2.should_set_compliance_number())
        self.assertTrue(self.moderation_request3.should_set_compliance_number())

        # Now let's check that the compliance number should not be overridden
        self.moderation_request2.set_compliance_number()
        self.assertFalse(self.moderation_request1.should_set_compliance_number())

    def test_rejection_makes_the_previous_actions_archived(self):
        previous_action_1 = self.moderation_request1.actions.create(
            by_user=self.user,
            action=constants.ACTION_APPROVED,
        )
        previous_action_2 = self.moderation_request1.actions.create(
            by_user=self.user2,
            action=constants.ACTION_RESUBMITTED,
        )

        self.assertFalse(previous_action_1.is_archived)
        self.assertFalse(previous_action_2.is_archived)

        self.moderation_request1.update_status(
            action=constants.ACTION_REJECTED,
            by_user=self.user,
            message='Rejecting this',
        )

        previous_action_1.refresh_from_db()
        previous_action_2.refresh_from_db()
        self.assertTrue(previous_action_1.is_archived)
        self.assertTrue(previous_action_2.is_archived)

    @patch('djangocms_moderation.models.generate_compliance_number')
    def test_compliance_number(self, mock_uuid):
        mock_uuid.return_value = 'abc123'

        request = ModerationRequest.objects.create(
            content_object=self.pg1,
            language='en',
            is_active=True,
            collection=self.collection1,
        )
        self.assertEqual(mock_uuid.call_count, 0)

        request.set_compliance_number()
        self.assertEqual(mock_uuid.call_count, 1)
        self.assertEqual(request.compliance_number, 'abc123')

    def test_compliance_number_sequential_number_backend(self):
        self.wf2.compliance_number_backend = 'djangocms_moderation.backends.sequential_number_backend'
        request = ModerationRequest.objects.create(
            content_object=self.pg1,
            language='en',
            collection=self.collection2,
        )
        request.refresh_from_db()
        self.assertIsNone(request.compliance_number)

        expected = str(request.pk)
        request.set_compliance_number()
        request.refresh_from_db()
        self.assertEqual(request.compliance_number, expected)

    def test_compliance_number_sequential_number_with_identifier_prefix_backend(self):
        self.wf2.compliance_number_backend = (
            'djangocms_moderation.backends.sequential_number_with_identifier_prefix_backend'
        )
        self.wf2.identifier = 'SSO'

        request = ModerationRequest.objects.create(
            content_object=self.pg1,
            language='en',
            collection=self.collection2,
        )
        request.refresh_from_db()
        self.assertIsNone(request.compliance_number)

        expected = "SSO{}".format(request.pk)
        request.set_compliance_number()
        request.refresh_from_db()
        self.assertEqual(request.compliance_number, expected)


class ModerationRequestActionTest(BaseTestCase):

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
        new_request = ModerationRequest.objects.create(
            content_object=self.pg2,
            language='en',
            collection=self.collection1,
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
        self.cp = ConfirmationPage.objects.create(name='Checklist Form')
        self.role1.confirmation_page = self.cp
        self.role1.save()

    def test_get_absolute_url(self):
        url = reverse('admin:cms_moderation_confirmation_page', args=(self.cp.pk,))
        self.assertEqual(self.cp.get_absolute_url(), url)

    def test_is_valid_returns_false_when_no_form_submission(self):
        result = self.cp.is_valid(active_request=self.moderation_request1, for_step=self.wf1st1,)
        self.assertFalse(result)

    def test_is_valid_returns_true_when_form_submission_exists(self):
        ConfirmationFormSubmission.objects.create(
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


class ModerationCollectionTest(BaseTestCase):
    def test_create_moderation_request_from_content_object(self):
        def _moderation_requests_count(obj, collection=None):
            """
            How many moderation requests are there [for a given collection]
            :return: <bool>
            """
            content_type = ContentType.objects.get_for_model(obj)
            queryset = ModerationRequest.objects.filter(
                content_type=content_type,
                object_id=obj.pk,
            )
            if collection:
                queryset = queryset.filter(collection=collection)
            return queryset.count()

        collection1 = ModerationCollection.objects.create(
            author=self.user, name='My collection 1', workflow=self.wf1
        )
        collection2 = ModerationCollection.objects.create(
            author=self.user, name='My collection 2', workflow=self.wf1
        )

        page1 = create_page(title='My page 1', template='page.html', language='en',)
        page2 = create_page(title='My page 2', template='page.html', language='en',)

        self.assertEqual(0, _moderation_requests_count(page1))
        # Add `page1` to `collection1`
        collection1.create_moderation_request_from_content_object(page1)
        self.assertEqual(1, _moderation_requests_count(page1))
        self.assertEqual(1, _moderation_requests_count(page1, collection1))

        # Adding the same object to the same collection is fine, it is already
        # there so it won't be added again
        collection1.create_moderation_request_from_content_object(page1)
        self.assertEqual(1, _moderation_requests_count(page1, collection1))
        self.assertEqual(1, _moderation_requests_count(page1))

        # This should not work as `page1` is already part of `collection1`
        with self.assertRaises(ObjectAlreadyInCollection):
            collection2.create_moderation_request_from_content_object(page1)
        # But we can add `page2` to the `collection1` as it is not there yet
        self.assertEqual(0, _moderation_requests_count(page2))
        collection1.create_moderation_request_from_content_object(page2)
        self.assertEqual(1, _moderation_requests_count(page2))
        self.assertEqual(1, _moderation_requests_count(page2, collection1))
        self.assertEqual(1, _moderation_requests_count(page1, collection1))
