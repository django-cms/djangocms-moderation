import unittest
from unittest import mock

from django.contrib.admin.helpers import ACTION_CHECKBOX_NAME
from django.contrib.auth.models import Group
from django.test import TransactionTestCase
from django.urls import reverse

from cms.test_utils.testcases import CMSTestCase
from cms.test_utils.util.context_managers import signal_tester

from djangocms_versioning.constants import DRAFT, PUBLISHED
from djangocms_versioning.models import Version

from djangocms_moderation import constants
from djangocms_moderation.admin import ModerationRequestTreeAdmin
from djangocms_moderation.constants import ACTION_REJECTED
from djangocms_moderation.models import (
    ModerationRequest,
    ModerationRequestTreeNode,
    Role,
)
from djangocms_moderation.signals import published

from .utils import factories


def get_url_data(cls, action):
    get_resp = cls.client.get(cls.url)
    data = {
        "action": action,
        ACTION_CHECKBOX_NAME: [str(f.pk) for f in get_resp.context['cl'].queryset]
    }
    return data


class ApproveSelectedTest(CMSTestCase):

    def setUp(self):
        # Set up the db data
        self.role1 = Role.objects.create(name="Role 1", user=factories.UserFactory(is_staff=True, is_superuser=True))
        self.role2 = Role.objects.create(name="Role 2", user=factories.UserFactory(is_staff=True, is_superuser=True))
        self.collection = factories.ModerationCollectionFactory(
            author=self.role1.user, status=constants.IN_REVIEW)
        self.collection.workflow.steps.create(role=self.role1, is_required=True, order=1)
        self.collection.workflow.steps.create(role=self.role2, is_required=True, order=1)
        # NOTE: Setting ids because we want the ids of the requests to be
        # different to the ids of the nodes. This will give us confidence
        # that the ids of the correct objects are being passed to the
        # correct places.
        self.moderation_request1 = factories.ModerationRequestFactory(
            id=1, collection=self.collection)
        self.moderation_request2 = factories.ModerationRequestFactory(
            id=2, collection=self.collection)
        self.root1 = factories.RootModerationRequestTreeNodeFactory(
            id=4, moderation_request=self.moderation_request1)
        factories.ChildModerationRequestTreeNodeFactory(
            id=5, moderation_request=self.moderation_request2, parent=self.root1)
        self.root2 = factories.RootModerationRequestTreeNodeFactory(
            id=6, moderation_request=self.moderation_request2)
        # Request 1 is approved, request 2 is started
        self.moderation_request1.actions.create(by_user=self.role1.user, action=constants.ACTION_STARTED)
        self.moderation_request2.actions.create(by_user=self.role1.user, action=constants.ACTION_STARTED)
        self.moderation_request1.update_status(constants.ACTION_APPROVED, self.role1.user)
        self.moderation_request1.update_status(constants.ACTION_APPROVED, self.role2.user)

        # Set up the url data
        self.url = reverse("admin:djangocms_moderation_moderationrequesttreenode_changelist")
        self.url += f"?moderation_request__collection__id={self.collection.pk}"

        # Asserts to check data set up is ok. Ideally wouldn't need them, but
        # the set up is so complex that it's safer to have them.
        self.assertFalse(self.moderation_request2.is_approved())
        self.assertTrue(self.moderation_request1.is_approved())

    @mock.patch("django.contrib.messages.success")
    @mock.patch("djangocms_moderation.admin.notify_collection_moderators")
    @mock.patch("djangocms_moderation.admin.notify_collection_author")
    def test_approve_selected(self, notify_author_mock, notify_moderators_mock, messages_mock):
        # Login as the collection author/role 1
        self.client.force_login(self.role1.user)

        # Select the approve action from the menu
        data = get_url_data(self, "approve_selected")
        response = self.client.post(self.url, data)
        # And now go to the view the action redirects to. This will
        # perform step1 of the approval process (as defined in the
        # workflow in the setUp method)
        response = self.client.post(response.url)

        # Check response
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, self.url)
        self.assertEqual(messages_mock.call_args[0][1], '1 request successfully approved')
        messages_mock.reset_mock()

        # Check correct users notified
        notify_author_mock.assert_called_once_with(
            collection=self.collection,
            moderation_requests=[self.moderation_request2],
            action=self.moderation_request2.get_last_action().action,
            by_user=self.role1.user,
        )
        notify_moderators_mock.assert_called_once_with(
            collection=self.collection,
            moderation_requests=[self.moderation_request2],
            action_obj=self.moderation_request2.get_last_action(),
        )
        # And reset mocks because we'll be needing to check this again
        # for step2
        notify_author_mock.reset_mock()
        notify_moderators_mock.reset_mock()

        # The status of the moderation requests hasn't changed yet
        # because there are 2 steps to approval and both are needed
        # for status to change
        self.assertFalse(self.moderation_request2.is_approved())
        self.assertTrue(self.moderation_request1.is_approved())

        # Collection status hasn't changed either
        self.collection.refresh_from_db()
        self.assertEqual(self.collection.status, constants.IN_REVIEW)

        # Now login as the user responsible for approving step2
        self.client.force_login(self.role2.user)

        # Select the approve action from the menu again
        data = get_url_data(self, "approve_selected")
        response = self.client.post(self.url, data)
        # And now go to the view the action redirects to. This will
        # perform step2 of the approval process (as defined in the
        # workflow in the setUp method)
        response = self.client.post(response.url)

        # Check response
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, self.url)
        self.assertEqual(messages_mock.call_args[0][1], '1 request successfully approved')

        # The status of the previously unapproved request has changed.
        # The other request stays as it is
        self.assertTrue(self.moderation_request2.is_approved())
        self.assertTrue(self.moderation_request1.is_approved())

        # The collection has been archived as both requests have been
        # approved now
        self.collection.refresh_from_db()
        self.assertEqual(self.collection.status, constants.ARCHIVED)

        # Correct users have been notified
        notify_author_mock.assert_called_once_with(
            collection=self.collection,
            moderation_requests=[self.moderation_request2],
            action=self.moderation_request2.get_last_action().action,
            by_user=self.role2.user,
        )
        self.assertFalse(notify_moderators_mock.called)

    @mock.patch("django.contrib.messages.success")
    @mock.patch("djangocms_moderation.admin.notify_collection_moderators")
    def test_approve_selected_sends_correct_emails_to_moderators(self, notify_moderators_mock, messages_mock):
        # Set up additional roles and user
        user3 = factories.UserFactory(is_staff=True, is_superuser=True)
        group = Group.objects.create(name="Group 1")
        user3.groups.add(group)
        role3 = Role.objects.create(name="Role 3", group=group)
        role4 = Role.objects.create(user=self.role1.user)
        # Set up two more steps
        self.collection.workflow.steps.create(role=role3, is_required=True, order=1)
        self.collection.workflow.steps.create(role=role4, is_required=True, order=1)
        self.role1.user.groups.add(group)
        # Set up one more, partially approved request
        moderation_request3 = factories.ModerationRequestFactory(id=3, collection=self.collection)
        moderation_request3.actions.create(by_user=self.role1.user, action=constants.ACTION_STARTED)
        moderation_request3.update_status(by_user=self.role1.user, action=constants.ACTION_APPROVED)
        moderation_request3.update_status(by_user=self.role2.user, action=constants.ACTION_APPROVED)
        factories.RootModerationRequestTreeNodeFactory(
            id=7, moderation_request=moderation_request3
        )

        # Login as the collection author/role1 user
        self.client.force_login(self.role1.user)
        data = get_url_data(self, "approve_selected")
        response = self.client.post(self.url, data)
        response = self.client.post(response.url)

        # Check response
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, self.url)
        self.assertEqual(messages_mock.call_args[0][1], '3 requests successfully approved')
        messages_mock.reset_mock()

        # First post as role1 user should notify mr1 and mr2 and mr3 moderators
        # The notify email will be sent accordingly. As mr1 and mr3 are in
        # different stages of approval compared to mr 2,
        # we need to send 2 emails to appropriate moderators
        self.assertEqual(notify_moderators_mock.call_count, 2)
        self.assertEqual(
            notify_moderators_mock.call_args_list[1],
            mock.call(collection=self.collection,
                      moderation_requests=[self.moderation_request1, moderation_request3],
                      action_obj=self.moderation_request1.get_last_action())
        )
        self.assertEqual(
            notify_moderators_mock.call_args_list[0],
            mock.call(collection=self.collection,
                      moderation_requests=[self.moderation_request2],
                      action_obj=self.moderation_request2.get_last_action())
        )
        notify_moderators_mock.reset_mock()

        # No moderation requests are approved yet
        self.assertFalse(self.moderation_request1.is_approved())
        self.assertFalse(self.moderation_request2.is_approved())
        self.assertFalse(moderation_request3.is_approved())

        response = self.client.post(self.url, data)
        response = self.client.post(response.url)

        # Check response
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, self.url)
        self.assertEqual(messages_mock.call_args[0][1], '2 requests successfully approved')
        messages_mock.reset_mock()

        # Second post approves m3 and mr1, but as this is the last stage of
        # the approval, there is no need for notification emails anymore
        self.assertEqual(notify_moderators_mock.call_count, 0)
        # moderation request 1 and 3 are now approved. Moderation request
        # 2 is not
        self.assertTrue(self.moderation_request1.is_approved())
        self.assertFalse(self.moderation_request2.is_approved())
        self.assertTrue(moderation_request3.is_approved())

        # moderation request 2 is not yet approved so collection should
        # still be in review
        self.collection.refresh_from_db()
        self.assertEqual(self.collection.status, constants.IN_REVIEW)

        self.client.force_login(self.role2.user)
        # user2 can approve only 1 request, mr2, so one notification email
        # should go out
        response = self.client.post(self.url, data)
        response = self.client.post(response.url)

        # Check response
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, self.url)
        self.assertEqual(messages_mock.call_args[0][1], '1 request successfully approved')
        messages_mock.reset_mock()

        notify_moderators_mock.assert_called_once_with(
            collection=self.collection,
            moderation_requests=[self.moderation_request2],
            action_obj=self.moderation_request2.get_last_action(),
        )
        notify_moderators_mock.reset_mock()

        # moderation request 2 is still not yet approved
        self.assertTrue(self.moderation_request1.is_approved())
        self.assertFalse(self.moderation_request2.is_approved())
        self.assertTrue(moderation_request3.is_approved())

        # moderation request 2 is not yet approved so collection should
        # still be in review
        self.collection.refresh_from_db()
        self.assertEqual(self.collection.status, constants.IN_REVIEW)

        self.client.force_login(user3)
        response = self.client.post(self.url, data)
        response = self.client.post(response.url)

        # Check response
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, self.url)
        self.assertEqual(messages_mock.call_args[0][1], '1 request successfully approved')
        messages_mock.reset_mock()

        notify_moderators_mock.assert_called_once_with(
            collection=self.collection,
            moderation_requests=[self.moderation_request2],
            action_obj=self.moderation_request2.get_last_action(),
        )
        notify_moderators_mock.reset_mock()

        self.assertTrue(self.moderation_request1.is_approved())
        self.assertFalse(self.moderation_request2.is_approved())
        self.assertTrue(moderation_request3.is_approved())

        # moderation request 2 is not yet approved so collection should
        # still be in review
        self.collection.refresh_from_db()
        self.assertEqual(self.collection.status, constants.IN_REVIEW)

        self.client.force_login(self.role1.user)
        response = self.client.post(self.url, data)
        response = self.client.post(response.url)

        # Check response
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, self.url)
        self.assertEqual(messages_mock.call_args[0][1], '1 request successfully approved')
        messages_mock.reset_mock()

        self.assertEqual(notify_moderators_mock.call_count, 0)

        self.assertTrue(self.moderation_request1.is_approved())
        self.assertTrue(self.moderation_request2.is_approved())
        self.assertTrue(moderation_request3.is_approved())

        # moderation request 2 is now approved so collection should
        # have been archived
        self.collection.refresh_from_db()
        self.assertEqual(self.collection.status, constants.ARCHIVED)

    def test_404_on_nonexisting_collection(self):
        self.client.force_login(self.role1.user)
        # Need to access the view directly to test for this
        url = reverse("admin:djangocms_moderation_moderationrequest_approve")
        url += "?ids=1,2&collection_id=12342"

        response = self.client.post(url)

        self.assertEqual(response.status_code, 404)

    def test_404_on_invalid_collection_id(self):
        self.client.force_login(self.role1.user)
        # Need to access the view directly to test for this
        url = reverse("admin:djangocms_moderation_moderationrequest_approve")
        url += "?ids=1,2&collection_id=aaa"

        response = self.client.post(url)

        self.assertEqual(response.status_code, 404)

    @mock.patch("djangocms_moderation.admin.notify_collection_moderators")
    @mock.patch("django.contrib.messages.success")
    @mock.patch(
        "djangocms_moderation.models.ModerationRequest.user_can_take_moderation_action",
        mock.Mock(return_value=False)
    )
    def test_view_doesnt_approve_when_user_cant_approve(self, messages_mock, notify_moderators_mock):
        self.client.force_login(self.role1.user)
        # Set up the url (need to access the view directly)
        url = reverse("admin:djangocms_moderation_moderationrequest_approve")
        url += "?ids=%d,%d&collection_id=%d" % (
            self.moderation_request1.pk, self.moderation_request2.pk, self.collection.pk)

        response = self.client.post(url)

        # Check response
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, self.url)
        self.assertEqual(messages_mock.call_args[0][1], '0 requests successfully approved')
        # No actions were approved
        self.assertFalse(self.moderation_request2.actions.filter(
            action=constants.ACTION_RESUBMITTED).exists())
        self.assertEqual(notify_moderators_mock.call_count, 0)

    def test_approve_view_when_using_get(self):
        self.client.force_login(self.role1.user)
        # Choose the approve_selected action from the dropdown
        data = get_url_data(self, "approve_selected")
        response = self.client.post(self.url, data)
        # And follow the redirect (with a GET call) to the view that does the approve
        response = self.client.get(response.url)

        # Smoke test the response. When using a GET call not a lot happens.
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.templates[0].name,
            'admin/djangocms_moderation/moderationrequest/approve_confirmation.html'
        )


class RejectSelectedTest(CMSTestCase):

    def setUp(self):
        # Set up the db data
        self.user = factories.UserFactory(is_staff=True, is_superuser=True)
        self.collection = factories.ModerationCollectionFactory(
            author=self.user, status=constants.IN_REVIEW)
        self.role1 = Role.objects.create(name="Role 1", user=self.user)
        self.role2 = Role.objects.create(name="Role 2", user=factories.UserFactory(is_staff=True, is_superuser=True))
        self.collection.workflow.steps.create(role=self.role1, is_required=True, order=1)
        self.collection.workflow.steps.create(role=self.role2, is_required=True, order=1)
        # NOTE: Setting ids because we want the ids of the requests to be
        # different to the ids of the nodes. This will give us confidence
        # that the ids of the correct objects are being passed to the
        # correct places.
        self.moderation_request1 = factories.ModerationRequestFactory(
            id=1, collection=self.collection)
        self.moderation_request2 = factories.ModerationRequestFactory(
            id=2, collection=self.collection)
        self.root1 = factories.RootModerationRequestTreeNodeFactory(
            id=4, moderation_request=self.moderation_request1)
        factories.ChildModerationRequestTreeNodeFactory(
            id=5, moderation_request=self.moderation_request2, parent=self.root1)
        self.root2 = factories.RootModerationRequestTreeNodeFactory(
            id=6, moderation_request=self.moderation_request2)
        # Request 1 is approved, request 2 is started
        self.moderation_request1.actions.create(by_user=self.user, action=constants.ACTION_STARTED)
        self.moderation_request2.actions.create(by_user=self.user, action=constants.ACTION_STARTED)
        self.moderation_request1.update_status(constants.ACTION_APPROVED, self.role1.user)
        self.moderation_request1.update_status(constants.ACTION_APPROVED, self.role2.user)

        # Login as the collection author
        self.client.force_login(self.user)

        # Set up the url data
        self.url = reverse("admin:djangocms_moderation_moderationrequesttreenode_changelist")
        self.url += f"?moderation_request__collection__id={self.collection.pk}"

        # Asserts to check data set up is ok. Ideally wouldn't need them, but
        # the set up is so complex that it's safer to have them.
        self.assertFalse(self.moderation_request2.is_approved())
        self.assertFalse(self.moderation_request2.is_rejected())
        self.assertTrue(self.moderation_request2.is_active)
        self.assertFalse(self.moderation_request2.actions.get().is_archived)
        self.assertTrue(self.moderation_request1.is_approved())

    @mock.patch("django.contrib.messages.success")
    @mock.patch("djangocms_moderation.admin.notify_collection_moderators")
    @mock.patch("djangocms_moderation.admin.notify_collection_author")
    def test_reject_selected_rejects_request(self, notify_author_mock, notify_moderators_mock, messages_mock):
        # Select the reject action from the menu
        data = get_url_data(self, "reject_selected")
        response = self.client.post(self.url, data)
        # And now go to the view the action redirects to
        response = self.client.post(response.url)

        # Response is correct
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, self.url)
        self.assertEqual(
            messages_mock.call_args[0][1],
            '1 request successfully submitted for rework'
        )

        # The rejected request has indeed been marked rejected. The
        # previous action on the rejected request has been archived. The
        # previously approved request has not changed its status
        self.assertFalse(self.moderation_request2.is_approved())
        self.assertTrue(self.moderation_request2.is_rejected())
        self.assertTrue(self.moderation_request2.is_active)
        moderation_request2_actions = self.moderation_request2.actions.all()
        self.assertEqual(moderation_request2_actions.count(), 2)
        self.assertTrue(moderation_request2_actions[0].is_archived)
        self.assertFalse(moderation_request2_actions[1].is_archived)
        self.assertTrue(self.moderation_request1.is_approved())

        # Expected users were notified
        self.assertFalse(notify_moderators_mock.called)
        notify_author_mock.assert_called_once_with(
            collection=self.collection,
            moderation_requests=[self.moderation_request2],
            action=self.moderation_request2.get_last_action().action,
            by_user=self.user,
        )

        # Collection still in review as version2 is still draft
        self.collection.refresh_from_db()
        self.assertEqual(self.collection.status, constants.IN_REVIEW)

    def test_reject_selected_view_when_using_get(self):
        # Choose the reject_selected action from the dropdown
        data = get_url_data(self, "reject_selected")
        response = self.client.post(self.url, data)
        # And follow the redirect (with a GET call) to the view that does the publish
        response = self.client.get(response.url)

        # Smoke test the response. When using a GET call not a lot happens.
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.templates[0].name,
            'admin/djangocms_moderation/moderationrequest/rework_confirmation.html'
        )

    def test_404_on_nonexisting_collection(self):
        # Need to access the view directly to test for this
        url = reverse("admin:djangocms_moderation_moderationrequest_rework")
        url += "?ids=1,2&collection_id=12342"

        response = self.client.post(url)

        self.assertEqual(response.status_code, 404)

    def test_404_on_invalid_collection_id(self):
        # Need to access the view directly to test for this
        url = reverse("admin:djangocms_moderation_moderationrequest_rework")
        url += "?ids=1,2&collection_id=aaa"

        response = self.client.post(url)

        self.assertEqual(response.status_code, 404)

    # TODO: This needs to be verified because unlike with other views
    # no code throws a 403 on non-author but the list of actions does
    # appear to filter the action dropdown for this user. Hard to say
    # what is the correct behaviour or if this test makes correct
    # assumptions in user set up.
    def test_reject_selected_action_cannot_be_accessed_if_not_collection_author(self):
        # Login as a user who is not the collection author
        self.client.force_login(self.role2.user)

        # Choose the reject_selected action from the dropdown
        data = get_url_data(self, "reject_selected")
        response = self.client.post(self.url, data)

        # The action is not on the page as available to somebody who is not
        # the author, therefore django will just return 200 as you're
        # trying to choose an action that isn't in the dropdown
        # (if anything had been resubmitted it would have been a 302)
        self.assertEqual(response.status_code, 200)

    @mock.patch("django.contrib.messages.success")
    @mock.patch(
        "djangocms_moderation.models.ModerationRequest.user_can_take_moderation_action",
        mock.Mock(return_value=False)
    )
    @mock.patch("djangocms_moderation.admin.notify_collection_moderators")
    @mock.patch("djangocms_moderation.admin.notify_collection_author")
    def test_view_doesnt_reject_when_user_cant_take_moderation_action(
        self, notify_author_mock, notify_moderators_mock, messages_mock
    ):
        # Set up the url (need to access the view directly)
        url = reverse("admin:djangocms_moderation_moderationrequest_rework")
        url += "?ids=%d,%d&collection_id=%d" % (
            self.moderation_request1.pk, self.moderation_request2.pk, self.collection.pk)

        response = self.client.post(url)

        # Check response
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, self.url)
        self.assertEqual(
            messages_mock.call_args[0][1],
            '0 requests successfully submitted for rework'
        )

        # The request has not changed
        self.assertFalse(self.moderation_request2.is_approved())
        self.assertFalse(self.moderation_request2.is_rejected())

        # Collection still in review
        self.collection.refresh_from_db()
        self.assertEqual(self.collection.status, constants.IN_REVIEW)

        # Nobody was notified
        self.assertFalse(notify_moderators_mock.called)
        self.assertFalse(notify_author_mock.called)


class PublishSelectedTest(CMSTestCase):

    def setUp(self):
        # Set up the db data
        self.user = factories.UserFactory(is_staff=True, is_superuser=True)
        self.collection = factories.ModerationCollectionFactory(
            author=self.user, status=constants.IN_REVIEW)
        self.role1 = Role.objects.create(name="Role 1", user=self.user)
        self.role2 = Role.objects.create(name="Role 2", user=factories.UserFactory(is_staff=True, is_superuser=True))
        self.collection.workflow.steps.create(role=self.role1, is_required=True, order=1)
        self.collection.workflow.steps.create(role=self.role2, is_required=True, order=1)
        # NOTE: Setting ids because we want the ids of the requests to be
        # different to the ids of the nodes. This will give us confidence
        # that the ids of the correct objects are being passed to the
        # correct places.
        self.moderation_request1 = factories.ModerationRequestFactory(
            id=1, collection=self.collection)
        self.moderation_request2 = factories.ModerationRequestFactory(
            id=2, collection=self.collection)
        self.root1 = factories.RootModerationRequestTreeNodeFactory(
            id=4, moderation_request=self.moderation_request1)

        self.root2 = factories.RootModerationRequestTreeNodeFactory(
            id=6, moderation_request=self.moderation_request2)
        # Request 1 is approved, request 2 is started
        self.moderation_request1.actions.create(by_user=self.user, action=constants.ACTION_STARTED)
        self.moderation_request2.actions.create(by_user=self.user, action=constants.ACTION_STARTED)
        self.moderation_request1.update_status(constants.ACTION_APPROVED, self.role1.user)
        self.moderation_request1.update_status(constants.ACTION_APPROVED, self.role2.user)

        # Login as the collection author
        self.client.force_login(self.user)

        # Set up the url data
        self.url = reverse("admin:djangocms_moderation_moderationrequesttreenode_changelist")
        self.url += f"?moderation_request__collection__id={self.collection.pk}"

        # Asserts to check data set up is ok. Ideally wouldn't need them, but
        # the set up is so complex that it's safer to have them.
        self.assertTrue(self.moderation_request1.is_active)
        self.assertTrue(self.moderation_request2.is_active)
        self.assertEqual(self.moderation_request1.version.state, DRAFT)
        self.assertEqual(self.moderation_request2.version.state, DRAFT)
        self.assertTrue(self.moderation_request1.is_approved())

    @mock.patch("django.contrib.messages.success")
    def test_publish_selected_publishes_approved_request(self, messages_mock):
        # Select the publish action from the menu

        data = get_url_data(self, "publish_selected")
        response = self.client.post(self.url, data)
        # And now go to the view the action redirects to
        response = self.client.post(response.url)

        # Response is correct
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, self.url)
        self.assertEqual(messages_mock.call_args[0][1], '1 request successfully published')

        # Check approved request was published and started request was not
        # NOTE: We can't do refresh_from_db() for Version, as it complains about
        # `state` field being changed directly
        version1 = Version.objects.get(pk=self.moderation_request1.version.pk)
        version2 = Version.objects.get(pk=self.moderation_request2.version.pk)
        self.moderation_request1.refresh_from_db()
        self.moderation_request2.refresh_from_db()
        self.assertEqual(version1.state, PUBLISHED)
        self.assertEqual(version2.state, DRAFT)
        self.assertFalse(self.moderation_request1.is_active)
        self.assertTrue(self.moderation_request2.is_active)

        # Collection still in review as version2 is still draft
        self.collection.refresh_from_db()
        self.assertEqual(self.collection.status, constants.IN_REVIEW)

    def test_signal_when_published(self):
        """
        A signal should be sent so further action can be taken when a moderation
        collection is being published.
        """
        data = get_url_data(self, "publish_selected")
        response = self.client.post(self.url, data)

        with signal_tester(published) as signal:
            # And now go to the view the action redirects to
            self.client.post(response.url)
            args, kwargs = signal.calls[0]
            published_mr = kwargs['moderation_requests']
            self.assertEqual(signal.call_count, 1)
            self.assertEqual(kwargs['sender'], ModerationRequest)
            self.assertEqual(kwargs['collection'], self.collection)
            self.assertEqual(kwargs['moderator'], self.collection.author)
            self.assertEqual(len(published_mr), 1)
            self.assertEqual(published_mr[0], self.moderation_request1)
            self.assertEqual(kwargs['workflow'], self.collection.workflow)

    @unittest.skip("Skip until collection status bugs fixed")
    @mock.patch("django.contrib.messages.success")
    def test_publish_selected_sets_collection_to_archived_if_all_requests_published(self, messages_mock):
        # Won't work because the approved_view sets the ARCHIVED state prior to how this test is setup
        self.moderation_request2.update_status(constants.ACTION_APPROVED, self.role1.user)
        self.moderation_request2.update_status(constants.ACTION_APPROVED, self.role2.user)

        # Select the publish action from the menu
        data = get_url_data(self, "publish_selected")
        response = self.client.post(self.url, data)
        # And now go to the view the action redirects to
        response = self.client.post(response.url)

        # Response is correct
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, self.url)
        self.assertEqual(messages_mock.call_args[0][1], '2 requests successfully published')

        # Check both approved request were published
        # NOTE: We can't do refresh_from_db() for Version, as it complains about
        # `state` field being changed directly
        version1 = Version.objects.get(pk=self.moderation_request1.version.pk)
        version2 = Version.objects.get(pk=self.moderation_request2.version.pk)
        self.moderation_request1.refresh_from_db()
        self.moderation_request2.refresh_from_db()
        self.assertEqual(version1.state, PUBLISHED)
        self.assertEqual(version2.state, PUBLISHED)
        self.assertFalse(self.moderation_request1.is_active)
        self.assertFalse(self.moderation_request2.is_active)

        # Collection should be archived as both requests are now published
        self.collection.refresh_from_db()
        self.assertEqual(self.collection.status, constants.ARCHIVED)

    def test_publish_selected_view_when_using_get(self):
        # Choose the publish_selected action from the dropdown
        data = get_url_data(self, "publish_selected")
        response = self.client.post(self.url, data)
        # And follow the redirect (with a GET call) to the view that does the publish
        response = self.client.get(response.url)

        # Smoke test the response. When using a GET call not a lot happens.
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.templates[0].name,
            'admin/djangocms_moderation/moderationrequest/publish_confirmation.html'
        )

    def test_404_on_nonexisting_collection(self):
        # Need to access the view directly to test for this
        url = reverse("admin:djangocms_moderation_moderationrequest_publish")
        url += "?ids=1,2&collection_id=12342"

        response = self.client.post(url)

        self.assertEqual(response.status_code, 404)

    def test_404_on_invalid_collection_id(self):
        # Need to access the view directly to test for this
        url = reverse("admin:djangocms_moderation_moderationrequest_publish")
        url += "?ids=1,2&collection_id=aaa"

        response = self.client.post(url)

        self.assertEqual(response.status_code, 404)

    def test_publish_selected_action_cannot_be_accessed_if_not_collection_author(self):
        # Login as a user who is not the collection author
        self.client.force_login(self.get_superuser())

        # Choose the resubmit_selected action from the dropdown
        data = get_url_data(self, "publish_selected")
        response = self.client.post(self.url, data)

        # The action is not on the page as available to somebody who is not
        # the author, therefore django will just return 200 as you're
        # trying to choose an action that isn't in the dropdown
        # (if anything had been resubmitted it would have been a 302)
        self.assertEqual(response.status_code, 200)

    def test_publish_selected_view_cannot_be_accessed_if_not_collection_author(self):
        # Login as a user who is not the collection author
        self.client.force_login(self.get_superuser())
        # Set up the url (need to access the view directly)
        url = reverse("admin:djangocms_moderation_moderationrequest_publish")
        url += "?ids=%d,%d&collection_id=%d" % (
            self.moderation_request1.pk, self.moderation_request2.pk, self.collection.pk)

        # POST directly to the view, don't go through actions
        response = self.client.post(url)

        # Check response
        self.assertEqual(response.status_code, 403)

        # Nothing is published
        version1 = Version.objects.get(pk=self.moderation_request1.version.pk)
        version2 = Version.objects.get(pk=self.moderation_request2.version.pk)
        self.moderation_request1.refresh_from_db()
        self.moderation_request2.refresh_from_db()
        self.assertEqual(version1.state, DRAFT)
        self.assertEqual(version2.state, DRAFT)
        self.assertTrue(self.moderation_request1.is_active)
        self.assertTrue(self.moderation_request2.is_active)

        # Collection still in review
        self.collection.refresh_from_db()
        self.assertEqual(self.collection.status, constants.IN_REVIEW)

    @mock.patch("django.contrib.messages.success")
    @mock.patch("djangocms_moderation.models.ModerationRequest.version_can_be_published", mock.Mock(return_value=False))
    def test_view_doesnt_publish_when_version_cant_be_published(self, messages_mock):
        # Set up the url (need to access the view directly)
        url = reverse("admin:djangocms_moderation_moderationrequest_publish")
        url += "?ids=%d,%d&collection_id=%d" % (
            self.moderation_request1.pk, self.moderation_request2.pk, self.collection.pk)

        response = self.client.post(url)

        # Check response
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, self.url)
        self.assertEqual(messages_mock.call_args[0][1], '0 requests successfully published')

        # Nothing is published
        version1 = Version.objects.get(pk=self.moderation_request1.version.pk)
        version2 = Version.objects.get(pk=self.moderation_request2.version.pk)
        self.moderation_request1.refresh_from_db()
        self.moderation_request2.refresh_from_db()
        self.assertEqual(version1.state, DRAFT)
        self.assertEqual(version2.state, DRAFT)
        self.assertTrue(self.moderation_request1.is_active)
        self.assertTrue(self.moderation_request2.is_active)

        # Collection still in review
        self.collection.refresh_from_db()
        self.assertEqual(self.collection.status, constants.IN_REVIEW)


class ResubmitSelectedTest(CMSTestCase):

    def setUp(self):
        # Set up the db data
        self.user = factories.UserFactory(is_staff=True, is_superuser=True)
        self.collection = factories.ModerationCollectionFactory(
            author=self.user, status=constants.IN_REVIEW)
        # NOTE: Setting ids because we want the ids of the requests to be
        # different to the ids of the nodes. This will give us confidence
        # that the ids of the correct objects are being passed to the
        # correct places.
        self.moderation_request1 = factories.ModerationRequestFactory(
            id=1, collection=self.collection)
        self.moderation_request2 = factories.ModerationRequestFactory(
            id=2, collection=self.collection)
        # Make self.moderation_request2 rejected
        self.moderation_request2.update_status(action=ACTION_REJECTED, by_user=self.user)
        self.root1 = factories.RootModerationRequestTreeNodeFactory(
            id=4, moderation_request=self.moderation_request1)
        factories.ChildModerationRequestTreeNodeFactory(
            id=5, moderation_request=self.moderation_request2, parent=self.root1)
        self.root2 = factories.RootModerationRequestTreeNodeFactory(
            id=6, moderation_request=self.moderation_request2)

        # Login as the collection author
        self.client.force_login(self.user)

        self.url = reverse("admin:djangocms_moderation_moderationrequesttreenode_changelist")
        self.url += f"?moderation_request__collection__id={self.collection.pk}"

        # Asserts to check data set up is ok. Ideally wouldn't need them, but
        # the set up is so complex that it's safer to have them.
        self.assertTrue(self.moderation_request2.is_rejected())
        self.assertTrue(self.moderation_request1.is_approved())
        self.assertEqual(self.collection.status, constants.IN_REVIEW)

    @mock.patch("djangocms_moderation.admin.notify_collection_moderators")
    @mock.patch("djangocms_moderation.admin.notify_collection_author")
    @mock.patch("django.contrib.messages.success")
    def test_resubmit_selected_resubmits_rejected_request(
        self, messages_mock, notify_author_mock, notify_moderators_mock
    ):
        # Choose the resubmit_selected action from the dropdown
        data = get_url_data(self, "resubmit_selected")
        response = self.client.post(self.url, data)
        # And follow the redirect to the view that does the resubmit
        response = self.client.post(response.url)

        # Response is correct
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, self.url)
        self.assertEqual(messages_mock.call_args[0][1], '1 request successfully resubmitted for review')

        # Rejected request was resubmitted and approved request did not change
        self.assertFalse(self.moderation_request2.is_rejected())
        self.assertTrue(self.moderation_request2.actions.filter(
            action=constants.ACTION_RESUBMITTED, by_user=self.user).exists())
        self.assertTrue(self.moderation_request1.is_approved())

        # Collection status has not changed
        self.collection.refresh_from_db()
        self.assertEqual(self.collection.status, constants.IN_REVIEW)

        # Expected users were notified
        self.assertFalse(notify_author_mock.called)
        notify_moderators_mock.assert_called_once_with(
            collection=self.collection,
            moderation_requests=[self.moderation_request2],
            action_obj=self.moderation_request2.get_last_action(),
        )

    def test_resubmit_selected_view_when_using_get(self):
        # Choose the resubmit_selected action from the dropdown
        data = get_url_data(self, "resubmit_selected")
        response = self.client.post(self.url, data)
        # And follow the redirect (with a GET call) to the view that does the resubmit
        response = self.client.get(response.url)

        # Smoke test the response. When using a GET call not a lot happens.
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.templates[0].name,
            'admin/djangocms_moderation/moderationrequest/resubmit_confirmation.html'
        )

    def test_404_on_nonexisting_collection(self):
        # Need to access the view directly to test for this
        url = reverse("admin:djangocms_moderation_moderationrequest_resubmit")
        url += "?ids=1,2&collection_id=12342"

        response = self.client.post(url)

        self.assertEqual(response.status_code, 404)

    def test_404_on_invalid_collection_id(self):
        # Need to access the view directly to test for this
        url = reverse("admin:djangocms_moderation_moderationrequest_resubmit")
        url += "?ids=1,2&collection_id=aaa"

        response = self.client.post(url)

        self.assertEqual(response.status_code, 404)

    @mock.patch("djangocms_moderation.admin.notify_collection_moderators")
    @mock.patch("django.contrib.messages.success")
    @mock.patch("djangocms_moderation.models.ModerationRequest.user_can_resubmit", mock.Mock(return_value=False))
    def test_view_doesnt_resubmit_when_user_cant_resubmit(self, messages_mock, notify_moderators_mock):
        # Set up the url (need to access the view directly)
        url = reverse("admin:djangocms_moderation_moderationrequest_resubmit")
        url += "?ids=%d,%d&collection_id=%d" % (
            self.moderation_request1.pk, self.moderation_request2.pk, self.collection.pk)

        response = self.client.post(url)

        # Check response
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, self.url)
        self.assertEqual(messages_mock.call_args[0][1], '0 requests successfully resubmitted for review')
        # No actions were resubmitted
        self.assertFalse(self.moderation_request2.actions.filter(
            action=constants.ACTION_RESUBMITTED).exists())
        self.assertEqual(notify_moderators_mock.call_count, 0)

    def test_resubmit_selected_action_cannot_be_accessed_if_not_collection_author(self):
        # Login as a user who is not the collection author
        self.client.force_login(self.get_superuser())

        # Choose the resubmit_selected action from the dropdown
        data = get_url_data(self, "resubmit_selected")
        response = self.client.post(self.url, data)

        # The action is not on the page as available to somebody who is not
        # the author, therefore django will just return 200 as you're
        # trying to choose an action that isn't in the dropdown
        # (if anything had been resubmitted it would have been a 302)
        self.assertEqual(response.status_code, 200)

    @mock.patch("djangocms_moderation.admin.notify_collection_moderators")
    def test_resubmit_selected_view_cannot_be_accessed_if_not_collection_author(self, notify_moderators_mock):
        # Login as a user who is not the collection author
        self.client.force_login(self.get_superuser())
        # Set up the url (need to access the view directly)
        url = reverse("admin:djangocms_moderation_moderationrequest_resubmit")
        url += "?ids=%d,%d&collection_id=%d" % (
            self.moderation_request1.pk, self.moderation_request2.pk, self.collection.pk)

        # POST directly to the view, don't go through actions
        response = self.client.post(url)

        self.assertEqual(response.status_code, 403)
        # Nothing is resubmitted
        self.assertFalse(self.moderation_request2.actions.filter(
            action=constants.ACTION_RESUBMITTED).exists())
        # Notifications not sent
        self.assertFalse(notify_moderators_mock.called)


class DeleteSelectedTest(CMSTestCase):
    def setUp(self):
        self.user = factories.UserFactory(is_staff=True, is_superuser=True)
        self.collection = factories.ModerationCollectionFactory(
            author=self.user, status=constants.IN_REVIEW)
        # NOTE: Setting ids because we want the ids of the requests to be
        # different to the ids of the nodes. This will give us confidence
        # that the ids of the correct objects are being passed to the
        # correct places.
        self.moderation_request1 = factories.ModerationRequestFactory(
            id=1, collection=self.collection)
        self.moderation_request2 = factories.ModerationRequestFactory(
            id=2, collection=self.collection)
        self.root1 = factories.RootModerationRequestTreeNodeFactory(
            id=4, moderation_request=self.moderation_request1)
        factories.ChildModerationRequestTreeNodeFactory(
            id=5, moderation_request=self.moderation_request2, parent=self.root1)
        self.root2 = factories.RootModerationRequestTreeNodeFactory(
            id=6, moderation_request=self.moderation_request2)

        self.url = reverse("admin:djangocms_moderation_moderationrequesttreenode_changelist")
        self.url += f"?moderation_request__collection__id={self.collection.pk}"

    @mock.patch.object(ModerationRequestTreeAdmin, "has_delete_permission", mock.Mock(return_value=True))
    def test_delete_selected_action_cannot_be_accessed_if_not_collection_author(self):
        # Login as a user who is not the collection author
        self.client.force_login(self.get_superuser())

        # Choose the delete_selected action from the dropdown
        data = get_url_data(self, "delete_selected")
        response = self.client.post(self.url, data)

        # The action is not on the page as available to somebody who is not
        # the author, therefore django will just return 200 as you're
        # trying to choose an action that isn't in the dropdown
        # (if anything had been deleted it would have been a 302)
        self.assertEqual(response.status_code, 200)

    @mock.patch.object(ModerationRequestTreeAdmin, "has_delete_permission", mock.Mock(return_value=True))
    @mock.patch("djangocms_moderation.admin.notify_collection_author")
    def test_delete_selected_view_cannot_be_accessed_if_not_collection_author(self, notify_author_mock):
        # Login as a user who is not the collection author
        self.client.force_login(self.get_superuser())
        # Set up the url
        url = reverse("admin:djangocms_moderation_moderationrequesttreenode_delete")
        url += "?ids={tree_ids}&collection_id={collection_id}".format(
            tree_ids=",".join([str(self.root1.pk), str(self.root2.pk)]),
            collection_id=str(self.collection.pk)
        )

        # POST directly to the view, don't go through actions
        response = self.client.post(url)

        self.assertEqual(response.status_code, 403)
        # Nothing is deleted
        self.assertEqual(ModerationRequest.objects.filter(collection=self.collection).count(), 2)
        # Collection not modified
        self.collection.refresh_from_db()
        self.assertEqual(self.collection.status, constants.IN_REVIEW)
        # Notifications not sent
        self.assertFalse(notify_author_mock.called)

    @mock.patch.object(ModerationRequestTreeAdmin, "has_delete_permission", mock.Mock(return_value=False))
    def test_delete_selected_action_cannot_be_accessed_without_delete_permission(self):
        # Login as the collection author
        self.client.force_login(self.user)
        # Choose the delete_selected action from the dropdown
        data = get_url_data(self, "remove_selected")
        response = self.client.post(self.url, data)

        self.assertEqual(response.status_code, 403)

    @mock.patch.object(ModerationRequestTreeAdmin, "has_delete_permission", mock.Mock(return_value=False))
    @mock.patch("djangocms_moderation.admin.notify_collection_author")
    def test_delete_selected_view_cannot_be_accessed_without_delete_permission(self, notify_author_mock):
        # Login as the collection author
        self.client.force_login(self.user)
        # Set up url
        url = reverse("admin:djangocms_moderation_moderationrequesttreenode_delete")
        url += "?ids={tree_ids}&collection_id={collection_id}".format(
            tree_ids=",".join([str(self.root1.pk), str(self.root2.pk)]),
            collection_id=str(self.collection.pk)
        )

        # POST directly to the view, don't go through actions
        response = self.client.post(url)

        self.assertEqual(response.status_code, 403)
        # Nothing is deleted
        self.assertEqual(ModerationRequest.objects.filter(collection=self.collection).count(), 2)
        # Collection not modified
        self.collection.refresh_from_db()
        self.assertEqual(self.collection.status, constants.IN_REVIEW)
        # Notifications not sent
        self.assertFalse(notify_author_mock.called)

    @mock.patch("django.contrib.messages.success")
    @mock.patch.object(ModerationRequestTreeAdmin, "has_delete_permission", mock.Mock(return_value=True))
    @mock.patch("djangocms_moderation.admin.notify_collection_moderators")
    @mock.patch("djangocms_moderation.admin.notify_collection_author")
    def test_delete_selected_deletes_all_relevant_objects(
        self, notify_author_mock, notify_moderators_mock, messages_mock
    ):
        """The selected ModerationRequest and ModerationRequestTreeNode objects should be deleted."""
        # Login as the collection author
        self.client.force_login(self.user)
        # Choose the delete_selected action from the dropdown
        data = get_url_data(self, "remove_selected")
        response = self.client.post(self.url, data)
        self.assertEqual(response.status_code, 302)

        # Now do the request the delete_selected action has led us to
        response = self.client.post(response.url)
        self.assertRedirects(response, self.url)
        self.assertEqual(messages_mock.call_args[0][1], '2 requests successfully deleted')
        # And check the requests have indeed been deleted
        self.assertEqual(ModerationRequest.objects.filter(collection=self.collection).count(), 0)
        # And correct notifications sent out
        notify_author_mock.assert_called_once_with(
            collection=self.collection,
            moderation_requests=[self.moderation_request1, self.moderation_request2],
            action=constants.ACTION_CANCELLED,
            by_user=self.user,
        )
        self.assertFalse(notify_moderators_mock.called)
        # All moderation requests were deleted, so collection should be archived
        self.collection.refresh_from_db()
        self.assertEqual(self.collection.status, constants.ARCHIVED)

    def test_delete_view_when_using_get(self):
        # Login as the collection author
        self.client.force_login(self.user)

        # Choose the delete_selected action from the dropdown
        data = get_url_data(self, "remove_selected")
        response = self.client.post(self.url, data)
        # And follow the redirect (with a GET call) to the view that does the approve
        response = self.client.get(response.url)

        # Smoke test the response. When using a GET call not a lot happens.
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.templates[0].name,
            'admin/djangocms_moderation/moderationrequest/delete_confirmation.html'
        )


class DeletedSelectedTransactionTest(TransactionTestCase):

    def setUp(self):
        # Create db data
        self.user = factories.UserFactory(is_staff=True, is_superuser=True)
        self.collection = factories.ModerationCollectionFactory(
            author=self.user, status=constants.IN_REVIEW)
        self.moderation_request1 = factories.ModerationRequestFactory(
            collection=self.collection)
        self.moderation_request2 = factories.ModerationRequestFactory(
            collection=self.collection)
        self.root1 = factories.RootModerationRequestTreeNodeFactory(
            moderation_request=self.moderation_request1)
        self.root2 = factories.RootModerationRequestTreeNodeFactory(
            moderation_request=self.moderation_request2)
        factories.ChildModerationRequestTreeNodeFactory(
            moderation_request=self.moderation_request1, parent=self.root1)

        # Login
        self.client.force_login(self.user)

        # Generate url and POST data
        self.url = reverse("admin:djangocms_moderation_moderationrequesttreenode_changelist")
        self.url += f"?moderation_request__collection__id={self.collection.pk}"
        self.data = get_url_data(self, "delete_selected")

    def tearDown(self):
        """Clear content type cache for page content's versionable.

        This is necessary, because TransactionTestCase clears the
        entire database after each test, meaning ContentType objects
        are recreated with new IDs. Cache kept old IDs, causing
        inability to retrieve versions for a given object.
        """
        del self.moderation_request1.version.versionable.content_types

    @mock.patch("djangocms_moderation.admin.messages.success")
    def test_deleting_is_wrapped_in_db_transaction(self, messages_mock):
        class FakeError(Exception):
            pass
        # Throw an exception to cause a db rollback.
        # Throwing FakeError as no actual code will ever throw it and
        # therefore catching this later in the test will not cover up a
        # genuine issue
        messages_mock.side_effect = FakeError

        # Choose the delete_selected action from the dropdown
        response = self.client.post(self.url, self.data)
        self.assertEqual(response.status_code, 302)

        # Now do the request the delete_selected action has led us to
        try:
            self.client.post(response.url, self.data)
        except FakeError:
            # This is what messages_mock should have thrown,
            # but we don't want the test to throw it.
            pass

        # Check neither the tree nodes nor the requests have been deleted.
        # The db transaction should have rolled back.
        self.assertEqual(ModerationRequestTreeNode.objects.all().count(), 3)
        self.assertEqual(ModerationRequest.objects.all().count(), 2)
