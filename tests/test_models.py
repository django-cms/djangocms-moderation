import json
from unittest.mock import patch

from django.contrib.auth.models import Permission, User
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from djangocms_moderation import constants
from djangocms_moderation.models import (
    ConfirmationFormSubmission,
    ConfirmationPage,
    ModerationCollection,
    ModerationRequest,
    ModerationRequestAction,
    ModerationRequestTreeNode,
    Role,
    Workflow,
    WorkflowStep,
)

from .utils import factories
from .utils.base import AssertQueryMixin, BaseTestCase


class RoleTest(AssertQueryMixin, BaseTestCase):
    def test_user_and_group_validation_error(self):
        role = Role.objects.create(name="New Role 1", user=self.user, group=self.group)
        self.assertRaisesMessage(
            ValidationError, "Can't pick both user and group. Only one.", role.clean
        )

    def test_user_is_assigned(self):
        # with user
        role = Role.objects.create(name="New Role 1", user=self.user)
        self.assertTrue(role.user_is_assigned(self.user))
        self.assertFalse(role.user_is_assigned(self.user2))
        # with group
        role = Role.objects.create(name="New Role 2", group=self.group)
        self.assertFalse(role.user_is_assigned(self.user))
        self.assertTrue(role.user_is_assigned(self.user2))

    def test_get_users_queryset(self):
        # with user
        role = Role.objects.create(name="New Role 1", user=self.user)
        self.assertQuerySetEqual(
            role.get_users_queryset(),
            User.objects.filter(pk=self.user.pk),
            transform=lambda x: x,
            ordered=False,
        )
        # with group
        role = Role.objects.create(name="New Role 2", group=self.group)
        self.assertQuerySetEqual(
            role.get_users_queryset(),
            User.objects.filter(pk__in=[self.user2.pk, self.user3.pk]),
            transform=lambda x: x,
            ordered=False,
        )


class WorkflowTest(BaseTestCase):
    def test_multiple_defaults_validation_error(self):
        workflow = Workflow.objects.create(name="New Workflow 3", is_default=False)
        workflow.clean()
        workflow = Workflow.objects.create(
            name="New Workflow 4", is_default=True
        )  # self.wf1 is default
        self.assertRaisesMessage(
            ValidationError,
            "Can't have two default workflows, only one is allowed.",
            workflow.clean,
        )

    def test_first_step(self):
        self.assertEqual(self.wf1.first_step, self.wf1st1)


class WorkflowStepTest(BaseTestCase):
    def test_get_next(self):
        self.assertEqual(self.wf1st1.get_next(), self.wf1st2)
        self.assertEqual(self.wf1st2.get_next(), self.wf1st3)
        self.assertIsNone(self.wf1st3.get_next())

    def test_get_next_required(self):
        self.assertEqual(self.wf1st1.get_next_required(), self.wf1st3)
        self.assertEqual(self.wf1st2.get_next_required(), self.wf1st3)
        self.assertIsNone(self.wf1st3.get_next_required())


class ModerationRequestTest(AssertQueryMixin, BaseTestCase):
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

    def test_version_can_be_published(self):
        self.assertFalse(self.moderation_request1.version_can_be_published())
        self.assertTrue(self.moderation_request2.version_can_be_published())
        # moderation_request3.version is already in published state
        self.assertFalse(self.moderation_request3.version_can_be_published())

    def test_is_rejected(self):
        self.assertFalse(self.moderation_request1.is_rejected())
        self.assertFalse(self.moderation_request2.is_rejected())
        self.assertTrue(self.moderation_request4.is_rejected())

    def test_get_first_action(self):
        self.assertEqual(
            self.moderation_request2.get_first_action(),
            self.moderation_request2.actions.first(),
        )

    def test_get_last_action(self):
        self.assertEqual(
            self.moderation_request2.get_last_action(),
            self.moderation_request2.actions.last(),
        )

    def test_get_pending_steps(self):
        self.assertQuerySetEqual(
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
        self.assertQuerySetEqual(
            self.moderation_request3.get_pending_steps(),
            WorkflowStep.objects.filter(workflow=self.wf3),
            transform=lambda x: x,
            ordered=False,
        )

    def test_get_pending_required_steps(self):
        self.assertQuerySetEqual(
            self.moderation_request1.get_pending_required_steps(),
            WorkflowStep.objects.filter(pk__in=[self.wf1st1.pk, self.wf1st3.pk]),
            transform=lambda x: x,
            ordered=False,
        )
        self.assertQuerySetEqual(
            self.moderation_request3.get_pending_required_steps(),
            WorkflowStep.objects.none(),
            transform=lambda x: x,
            ordered=False,
        )

        # Lets test with archived action
        self.assertQuerySetEqual(
            self.moderation_request2.get_pending_required_steps(),
            WorkflowStep.objects.none(),
            transform=lambda x: x,
            ordered=False,
        )

        # Make the last action archived
        last_action = self.moderation_request2.get_last_action()
        last_action.is_archived = True
        last_action.save()

        self.assertQuerySetEqual(
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
        self.assertEqual(
            self.moderation_request3.user_get_step(self.user2), self.wf3st2
        )

    def test_user_can_take_moderation_action(self):
        temp_user = User.objects.create_superuser(
            username="temp", email="temp@temp.com", password="temp"
        )
        self.assertFalse(
            self.moderation_request1.user_can_take_moderation_action(temp_user)
        )
        self.assertFalse(
            self.moderation_request3.user_can_take_moderation_action(self.user)
        )
        self.assertTrue(
            self.moderation_request3.user_can_take_moderation_action(self.user2)
        )

    def test_user_can_resubmit(self):
        temp_user = User.objects.create_superuser(
            username="temp", email="temp@temp.com", password="temp"
        )
        self.assertFalse(self.moderation_request1.user_can_resubmit(temp_user))
        author = self.moderation_request4.author
        # Only author can edit and resubmit
        self.assertTrue(self.moderation_request4.user_can_resubmit(author))
        self.assertFalse(self.moderation_request4.user_can_resubmit(self.user2))
        self.assertFalse(self.moderation_request4.user_can_resubmit(self.user3))

    def test_user_is_author(self):
        temp_user = User.objects.create_superuser(
            username="temp", email="temp@temp.com", password="temp"
        )
        self.assertFalse(self.moderation_request1.user_is_author(temp_user))
        self.assertFalse(self.moderation_request1.user_is_author(self.user2))
        self.assertTrue(self.moderation_request1.user_is_author(self.user))

    def test_user_can_view_comments(self):
        temp_user = User.objects.create_superuser(
            username="temp", email="temp@temp.com", password="temp"
        )
        self.assertFalse(self.moderation_request1.user_can_view_comments(temp_user))
        self.assertTrue(self.moderation_request1.user_can_view_comments(self.user2))
        self.assertTrue(self.moderation_request1.user_can_view_comments(self.user))

    def test_user_can_moderate(self):
        temp_user = User.objects.create_superuser(
            username="temp", email="temp@temp.com", password="temp"
        )
        self.assertFalse(self.moderation_request1.user_can_moderate(temp_user))
        self.assertFalse(self.moderation_request2.user_can_moderate(temp_user))
        self.assertFalse(self.moderation_request3.user_can_moderate(temp_user))

        # check that it doesn't allow access to users that aren't part of this moderation request
        user4 = User.objects.create_superuser(
            username="test4", email="test4@test.com", password="test4"
        )
        self.assertTrue(self.moderation_request4.user_can_moderate(self.user))
        self.assertTrue(self.moderation_request4.user_can_moderate(self.user2))
        self.assertTrue(self.moderation_request4.user_can_moderate(self.user3))
        self.assertFalse(self.moderation_request4.user_can_moderate(user4))

    def test_update_status_action_approved(self):
        self.moderation_request1.update_status(
            action=constants.ACTION_APPROVED, by_user=self.user, message="Approved"
        )
        self.assertTrue(self.moderation_request1.is_active)
        self.assertEqual(
            len(self.moderation_request1.actions.filter(is_archived=False)), 2
        )

    def test_update_status_action_rejected(self):
        self.moderation_request1.update_status(
            action=constants.ACTION_REJECTED, by_user=self.user, message="Rejected"
        )
        self.assertTrue(self.moderation_request1.is_active)
        self.assertEqual(len(self.moderation_request1.actions.all()), 2)

    def test_update_status_action_resubmitted(self):
        self.moderation_request1.update_status(
            action=constants.ACTION_RESUBMITTED,
            by_user=self.user,
            message="Resubmitting",
        )
        self.assertTrue(self.moderation_request1.is_active)
        self.assertEqual(len(self.moderation_request1.actions.all()), 2)

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
            by_user=self.user, action=constants.ACTION_APPROVED
        )
        previous_action_2 = self.moderation_request1.actions.create(
            by_user=self.user2, action=constants.ACTION_RESUBMITTED
        )

        self.assertFalse(previous_action_1.is_archived)
        self.assertFalse(previous_action_2.is_archived)

        self.moderation_request1.update_status(
            action=constants.ACTION_REJECTED,
            by_user=self.user,
            message="Rejecting this",
        )

        previous_action_1.refresh_from_db()
        previous_action_2.refresh_from_db()
        self.assertTrue(previous_action_1.is_archived)
        self.assertTrue(previous_action_2.is_archived)

    @patch("djangocms_moderation.models.generate_compliance_number")
    def test_compliance_number(self, mock_uuid):
        mock_uuid.return_value = "abc123"

        request = ModerationRequest.objects.create(
            version=self.pg4_version,
            language="en",
            is_active=True,
            collection=self.collection1,
            author=self.collection1.author,
        )
        self.assertEqual(mock_uuid.call_count, 0)

        request.set_compliance_number()
        self.assertEqual(mock_uuid.call_count, 1)
        self.assertEqual(request.compliance_number, "abc123")

    def test_compliance_number_sequential_number_backend(self):
        self.wf2.compliance_number_backend = (
            "djangocms_moderation.backends.sequential_number_backend"
        )
        self.wf2.save()
        request = ModerationRequest.objects.create(
            version=self.pg1_version,
            language="en",
            collection=self.collection2,
            author=self.collection2.author,
        )
        request.refresh_from_db()
        self.assertIsNone(request.compliance_number)

        expected = str(request.pk)
        request.set_compliance_number()
        request.refresh_from_db()
        self.assertEqual(request.compliance_number, expected)

    def test_compliance_number_sequential_number_with_identifier_prefix_backend(self):
        self.wf2.compliance_number_backend = "djangocms_moderation.backends.sequential_number_with_identifier_prefix_backend"  # noqa:E501
        self.wf2.identifier = "SSO"
        self.wf2.save()

        request = ModerationRequest.objects.create(
            version=self.pg1_version,
            language="en",
            collection=self.collection2,
            author=self.collection2.author,
        )
        request.refresh_from_db()
        self.assertIsNone(request.compliance_number)

        expected = f"SSO{request.pk}"
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
            version=self.pg2_version,
            language="en",
            collection=self.collection1,
            is_active=True,
            author=self.collection1.author,
        )
        new_action = new_request.actions.create(
            by_user=self.user, action=constants.ACTION_STARTED
        )
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
        self.cp = ConfirmationPage.objects.create(name="Checklist Form")
        self.role1.confirmation_page = self.cp
        self.role1.save()

    def test_get_absolute_url(self):
        url = reverse("admin:cms_moderation_confirmation_page", args=(self.cp.pk,))
        self.assertEqual(self.cp.get_absolute_url(), url)

    def test_is_valid_returns_false_when_no_form_submission(self):
        result = self.cp.is_valid(
            active_request=self.moderation_request1, for_step=self.wf1st1
        )
        self.assertFalse(result)

    def test_is_valid_returns_true_when_form_submission_exists(self):
        ConfirmationFormSubmission.objects.create(
            moderation_request=self.moderation_request1,
            for_step=self.wf1st1,
            by_user=self.user,
            data=json.dumps([{"label": "Question 1", "answer": "Yes"}]),
            confirmation_page=self.cp,
        )
        result = self.cp.is_valid(
            active_request=self.moderation_request1, for_step=self.wf1st1
        )
        self.assertTrue(result)

    def test_is_valid_returns_false_when_plain_content_not_reviewed(self):
        result = self.cp.is_valid(
            active_request=self.moderation_request1, for_step=self.wf1st1
        )
        self.assertFalse(result)


class ConfirmationFormSubmissionTest(BaseTestCase):
    def setUp(self):
        self.cp = ConfirmationPage.objects.create(name="Checklist Form")
        self.role1.confirmation_page = self.cp
        self.role1.save()

    def test_get_by_user_name(self):
        cfs = ConfirmationFormSubmission.objects.create(
            moderation_request=self.moderation_request1,
            for_step=self.wf1st1,
            by_user=self.user,
            data=json.dumps([{"label": "Question 1", "answer": "Yes"}]),
            confirmation_page=self.cp,
        )
        self.assertEqual(cfs.get_by_user_name(), self.user.username)


class ModerationCollectionTest(BaseTestCase):
    def setUp(self):
        self.collection1 = ModerationCollection.objects.create(
            author=self.user, name="My collection 1", workflow=self.wf1
        )
        self.collection2 = ModerationCollection.objects.create(
            author=self.user, name="My collection 2", workflow=self.wf1
        )

    def test_job_id(self):
        self.assertEqual(str(self.collection1.pk), self.collection1.job_id)
        self.assertEqual(str(self.collection2.pk), self.collection2.job_id)

    def test_is_cancellable(self):
        fixtures = (
            (constants.CANCELLED, False),
            (constants.COLLECTING, True),
            (constants.IN_REVIEW, True),
            (constants.ARCHIVED, False),
        )
        # Run these fixtures with collection author
        for fixture in fixtures:
            self.collection1.status = fixture[0]
            self.collection1.save()
            self.assertEqual(self.collection1.is_cancellable(self.user), fixture[1])

        # Run with different user, they should not be able to cancel
        for fixture in fixtures:
            self.collection1.status = fixture[0]
            self.collection1.save()
            self.assertFalse(self.collection1.is_cancellable(self.user2))

    def test_can_cancel_permission(self):
        # create non-admin, staff user with cancel_collection permission
        user_who_can_cancel = factories.UserFactory(is_staff=True)
        user_who_can_cancel.user_permissions.add(Permission.objects.get(
            content_type__app_label='djangocms_moderation',
            codename='cancel_moderationcollection'
        ))
        collection = factories.ModerationCollectionFactory(
            author=user_who_can_cancel, status=constants.COLLECTING
        )
        self.assertTrue(collection.is_cancellable(user_who_can_cancel))

    def test_cannot_cancel_permission(self):
        # create non-admin, staff user without cancel_collection permission
        user_who_cannot_cancel = factories.UserFactory(is_staff=True)

        # create a collection by user.
        collection = factories.ModerationCollectionFactory(
            author=user_who_cannot_cancel, status=constants.COLLECTING
        )
        self.assertFalse(collection.is_cancellable(user_who_cannot_cancel))

    @patch.object(ModerationRequest, "is_approved")
    def test_should_be_archived(self, is_approved_mock):
        self.collection1.status = constants.COLLECTING
        self.collection1.save()
        self.assertFalse(self.collection1.should_be_archived())

        self.collection1.status = constants.ARCHIVED
        self.collection1.save()
        self.assertFalse(self.collection1.should_be_archived())

        self.collection1.status = constants.IN_REVIEW
        self.collection1.save()
        self.assertTrue(self.collection1.should_be_archived())

        ModerationRequest.objects.create(
            version=self.pg1_version,
            collection=self.collection1,
            is_active=True,
            author=self.collection1.author,
        )
        is_approved_mock.return_value = False
        self.assertFalse(self.collection1.should_be_archived())

        is_approved_mock.return_value = True
        self.assertTrue(self.collection1.should_be_archived())

    def test_allow_submit_for_review(self):
        self.collection1.status = constants.COLLECTING
        self.collection1.save()
        # This is false, as we don't have any moderation requests in this collection
        self.assertFalse(self.collection1.allow_submit_for_review(user=self.user))

        ModerationRequest.objects.create(
            version=self.pg1_version,
            collection=self.collection1,
            is_active=True,
            author=self.collection1.author,
        )
        self.assertTrue(self.collection1.allow_submit_for_review(user=self.user))
        # Only collection author can submit
        self.assertFalse(self.collection1.allow_submit_for_review(user=self.user2))

        self.collection1.status = constants.IN_REVIEW
        self.collection1.save()
        self.assertFalse(self.collection1.allow_submit_for_review(user=self.user))

    @patch("djangocms_moderation.models.notify_collection_moderators")
    def test_submit_for_review(self, mock_ncm):
        ModerationRequest.objects.create(
            version=self.pg1_version,
            language="en",
            collection=self.collection1,
            author=self.collection1.author,
        )
        ModerationRequest.objects.create(
            version=self.pg3_version,
            language="en",
            collection=self.collection1,
            author=self.collection1.author,
        )

        self.assertFalse(
            ModerationRequestAction.objects.filter(
                moderation_request__collection=self.collection1
            ).exists()
        )

        self.collection1.status = constants.COLLECTING
        self.collection1.save()

        self.collection1.submit_for_review(self.user, None)
        self.assertEqual(1, mock_ncm.call_count)

        self.collection1.refresh_from_db()
        # Collection should lock itself
        self.assertEqual(self.collection1.status, constants.IN_REVIEW)
        # We will now have 2 actions with status STARTED.
        self.assertEqual(
            2,
            ModerationRequestAction.objects.filter(
                moderation_request__collection=self.collection1,
                action=constants.ACTION_STARTED,
            ).count(),
        )

    def test_cancel(self):
        active_request = ModerationRequest.objects.create(
            version=self.pg1_version,
            collection=self.collection1,
            is_active=True,
            author=self.collection1.author,
        )
        ModerationRequest.objects.create(
            version=self.pg3_version,
            collection=self.collection1,
            is_active=False,
            author=self.collection1.author,
        )

        self.collection1.status = constants.COLLECTING
        self.collection1.save()

        self.collection1.cancel(self.user)

        self.collection1.refresh_from_db()
        self.assertEqual(self.collection1.status, constants.CANCELLED)

        # Only 1 active request will be cancelled
        actions = ModerationRequestAction.objects.filter(
            moderation_request__collection=self.collection1,
            action=constants.ACTION_CANCELLED,
        )
        self.assertEqual(1, actions.count())
        self.assertEqual(actions[0].moderation_request, active_request)


class AddVersionTestCase(AssertQueryMixin, TestCase):

    def setUp(self):
        self.collection = factories.ModerationCollectionFactory()

    def test_add_version_as_parent(self):
        version = factories.PollVersionFactory()

        moderation_request, added_items = self.collection.add_version(version)

        self.assertEqual(ModerationRequest.objects.all().count(), 1)
        self.assertEqual(ModerationRequest.objects.get(), moderation_request)
        self.assertEqual(moderation_request.version, version)
        self.assertEqual(ModerationRequestTreeNode.objects.all().count(), 1)
        self.assertEqual(
            ModerationRequestTreeNode.objects.get().moderation_request,
            moderation_request
        )
        self.assertEqual(added_items, 1)

    def test_add_version_with_parent(self):
        version = factories.PollVersionFactory()
        parent = factories.RootModerationRequestTreeNodeFactory(
            moderation_request__collection=self.collection)

        moderation_request, added_items = self.collection.add_version(version, parent)

        self.assertEqual(ModerationRequest.objects.all().count(), 2)
        self.assertEqual(
            ModerationRequest.objects.exclude(pk=parent.moderation_request.pk).get(),
            moderation_request
        )
        self.assertEqual(moderation_request.version, version)
        self.assertEqual(ModerationRequestTreeNode.objects.all().count(), 2)
        self.assertEqual(
            ModerationRequestTreeNode.objects.exclude(pk=parent.pk).get().moderation_request,
            moderation_request
        )
        self.assertEqual(added_items, 1)

    def test_add_version_duplicate_with_same_parent(self):
        version = factories.PollVersionFactory()
        parent = factories.RootModerationRequestTreeNodeFactory(
            moderation_request__collection=self.collection)
        child = factories.ChildModerationRequestTreeNodeFactory(
            parent=parent,
            moderation_request__version=version,
            moderation_request__collection=self.collection
        )

        # Add the same version to the same collection under the same parent
        moderation_request, added_items = self.collection.add_version(version, parent)

        self.assertEqual(ModerationRequest.objects.all().count(), 2)
        self.assertQuerySetEqual(
            ModerationRequest.objects.all(),
            [parent.moderation_request.pk, child.moderation_request.pk],
            transform=lambda o: o.pk
        )
        self.assertEqual(ModerationRequestTreeNode.objects.all().count(), 2)
        self.assertQuerySetEqual(
            ModerationRequestTreeNode.objects.all(),
            [parent.pk, child.pk],
            transform=lambda o: o.pk
        )
        self.assertEqual(added_items, 0)
        self.assertEqual(moderation_request, child.moderation_request)

    def test_add_version_duplicate_with_different_parent(self):
        version = factories.PollVersionFactory()
        root = factories.RootModerationRequestTreeNodeFactory()
        child = factories.ChildModerationRequestTreeNodeFactory(
            parent=root,
            moderation_request__version=version,
            moderation_request__collection=self.collection
        )
        parent = factories.RootModerationRequestTreeNodeFactory(
            moderation_request__collection=self.collection)

        # Add the same version to the same collection under a different parent
        moderation_request, added_items = self.collection.add_version(version, parent)

        self.assertEqual(ModerationRequest.objects.all().count(), 3)
        self.assertQuerySetEqual(
            ModerationRequest.objects.all(),
            [root.moderation_request.pk, child.moderation_request.pk, parent.moderation_request.pk],
            transform=lambda o: o.pk
        )
        all_nodes = ModerationRequestTreeNode.objects.all()
        self.assertEqual(all_nodes.count(), 4)
        self.assertIn(parent, all_nodes)
        self.assertIn(child, all_nodes)
        self.assertIn(root, all_nodes)
        added_node = ModerationRequestTreeNode.objects.exclude(
            pk__in=[child.pk, parent.pk, root.pk]).get()
        self.assertEqual(added_node.moderation_request, child.moderation_request)
        self.assertEqual(added_items, 0)
        self.assertEqual(moderation_request, child.moderation_request)

    def test_add_version_duplicate_for_parent(self):
        version = factories.PollVersionFactory()
        parent = factories.RootModerationRequestTreeNodeFactory(
            moderation_request__collection=self.collection,
            moderation_request__version=version
        )

        # Add the same version to the same collection as parent
        moderation_request, added_items = self.collection.add_version(version)

        self.assertEqual(ModerationRequest.objects.all().count(), 1)
        self.assertEqual(ModerationRequest.objects.get(), parent.moderation_request)
        self.assertEqual(ModerationRequestTreeNode.objects.all().count(), 1)
        self.assertEqual(ModerationRequestTreeNode.objects.get(), parent)
        self.assertEqual(added_items, 0)
        self.assertEqual(moderation_request, parent.moderation_request)
