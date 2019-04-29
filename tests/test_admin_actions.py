import mock

from django.contrib.admin import ACTION_CHECKBOX_NAME
from django.contrib.auth.models import Group
from django.test import TransactionTestCase
from django.urls import reverse

from cms.test_utils.testcases import CMSTestCase

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

from .utils import factories


class ApproveSelectedTest(CMSTestCase):

    def setUp(self):
        self.user = factories.UserFactory(is_staff=True, is_superuser=True)
        self.user2 = factories.UserFactory(is_staff=True, is_superuser=True)
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

        self.role1 = Role.objects.create(name="Role 1", user=self.user)
        self.role2 = Role.objects.create(name="Role 2", user=self.user2)
        self.collection.workflow.steps.create(role=self.role1, is_required=True, order=1)
        self.collection.workflow.steps.create(role=self.role2, is_required=True, order=1)

        self.moderation_request1.actions.create(by_user=self.user, action=constants.ACTION_STARTED)
        self.moderation_request2.actions.create(by_user=self.user, action=constants.ACTION_STARTED)
        self.moderation_request1.update_status(constants.ACTION_APPROVED, self.role1.user)
        self.moderation_request1.update_status(constants.ACTION_APPROVED, self.role2.user)

    @mock.patch("djangocms_moderation.admin.notify_collection_moderators")
    @mock.patch("djangocms_moderation.admin.notify_collection_author")
    def test_approve_selected(self, notify_author_mock, notify_moderators_mock):
        # Login as the collection author
        self.client.force_login(self.user)
        data = {
            "action": "approve_selected",
            ACTION_CHECKBOX_NAME: [str(self.root1.pk), str(self.root2.pk)]
        }
        self.assertFalse(self.moderation_request2.is_approved())
        self.assertTrue(self.moderation_request1.is_approved())

        url = reverse("admin:djangocms_moderation_moderationrequesttreenode_changelist")
        url += "?moderation_request__collection__id={}".format(self.collection.pk)
        response = self.client.post(url, data)
        self.client.post(response.url)

        notify_author_mock.assert_called_once_with(
            collection=self.collection,
            moderation_requests=[self.moderation_request2],
            action=self.moderation_request2.get_last_action().action,
            by_user=self.user,
        )
        notify_moderators_mock.assert_called_once_with(
            collection=self.collection,
            moderation_requests=[self.moderation_request2],
            action_obj=self.moderation_request2.get_last_action(),
        )
        notify_author_mock.reset_mock()
        notify_moderators_mock.reset_mock()

        # There are 2 steps so we need to approve both to get mr2 approved
        self.assertFalse(self.moderation_request2.is_approved())
        self.assertTrue(self.moderation_request1.is_approved())
        self.collection.refresh_from_db()
        self.assertEqual(self.collection.status, constants.IN_REVIEW)
        self.client.force_login(self.user2)

        response = self.client.post(url, data)
        self.client.post(response.url)

        self.assertTrue(self.moderation_request2.is_approved())
        self.assertTrue(self.moderation_request1.is_approved())
        self.collection.refresh_from_db()
        self.assertEqual(self.collection.status, constants.ARCHIVED)
        notify_author_mock.assert_called_once_with(
            collection=self.collection,
            moderation_requests=[self.moderation_request2],
            action=self.moderation_request2.get_last_action().action,
            by_user=self.user2,
        )
        self.assertFalse(notify_moderators_mock.called)

    @mock.patch("djangocms_moderation.admin.notify_collection_moderators")
    def test_approve_selected_sends_correct_emails(self, notify_moderators_mock):
        user3 = factories.UserFactory(is_staff=True, is_superuser=True)
        group = Group.objects.create(name="Group 1")
        user3.groups.add(group)
        role3 = Role.objects.create(name="Role 3", group=group)
        role4 = Role.objects.create(user=self.user)
        # Add two more steps
        self.collection.workflow.steps.create(role=role3, is_required=True, order=1)
        self.collection.workflow.steps.create(role=role4, is_required=True, order=1)
        self.user.groups.add(group)

        # Login as the collection author
        self.client.force_login(self.user)

        # Add one more, partially approved request
        moderation_request3 = factories.ModerationRequestFactory(id=3, collection=self.collection)
        moderation_request3.actions.create(by_user=self.user, action=constants.ACTION_STARTED)
        moderation_request3.update_status(by_user=self.user, action=constants.ACTION_APPROVED)
        moderation_request3.update_status(by_user=self.user2, action=constants.ACTION_APPROVED)
        root3 = factories.RootModerationRequestTreeNodeFactory(
            id=7, moderation_request=moderation_request3)

        data = {
            "action": "approve_selected",
            ACTION_CHECKBOX_NAME: [str(self.root1.pk), str(self.root2.pk), str(root3.pk)]
        }

        # First post as `self.user` should notify mr1 and mr2 and mr3 moderators
        url = reverse("admin:djangocms_moderation_moderationrequesttreenode_changelist")
        url += "?moderation_request__collection__id={}".format(self.collection.pk)
        response = self.client.post(url, data)
        # The notify email will be send accordingly. As mr1 and mr3 are in the
        # different stages of approval compared to mr 2,
        # we need to send 2 emails to appropriate moderators
        self.client.post(response.url)
        self.assertEqual(notify_moderators_mock.call_count, 2)
        self.assertEqual(
            notify_moderators_mock.call_args_list[1],
            mock.call(collection=self.collection,
                      moderation_requests=[self.moderation_request1, moderation_request3],
                      action_obj=self.moderation_request1.get_last_action()
                      )
        )

        self.assertEqual(
            notify_moderators_mock.call_args_list[0],
            mock.call(collection=self.collection,
                      moderation_requests=[self.moderation_request2],
                      action_obj=self.moderation_request2.get_last_action(),
                      )
        )
        self.assertFalse(self.moderation_request1.is_approved())
        self.assertFalse(moderation_request3.is_approved())

        notify_moderators_mock.reset_mock()
        response = self.client.post(url, data)
        self.client.post(response.url)
        # Second post approves m3 and mr1, but as this is the last stage of
        # the approval, there is no need for notification emails anymore
        self.assertEqual(notify_moderators_mock.call_count, 0)
        self.assertTrue(self.moderation_request1.is_approved())
        self.assertTrue(moderation_request3.is_approved())

        self.client.force_login(self.user2)
        # user2 can approve only 1 request, mr2, so one notification email
        # should go out
        response = self.client.post(url, data)
        self.client.post(response.url)
        notify_moderators_mock.assert_called_once_with(
            collection=self.collection,
            moderation_requests=[self.moderation_request2],
            action_obj=self.moderation_request2.get_last_action(),
        )

        # Not all request have been fully approved
        self.collection.refresh_from_db()
        self.assertEqual(self.collection.status, constants.IN_REVIEW)


class RejectSelectedTest(CMSTestCase):

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

        role1 = Role.objects.create(name="Role 1", user=self.user)
        role2 = Role.objects.create(name="Role 2", user=factories.UserFactory(is_staff=True, is_superuser=True))
        self.collection.workflow.steps.create(role=role1, is_required=True, order=1)
        self.collection.workflow.steps.create(role=role2, is_required=True, order=1)

        self.moderation_request1.actions.create(by_user=self.user, action=constants.ACTION_STARTED)
        self.moderation_request2.actions.create(by_user=self.user, action=constants.ACTION_STARTED)
        self.moderation_request1.update_status(constants.ACTION_APPROVED, role1.user)
        self.moderation_request1.update_status(constants.ACTION_APPROVED, role2.user)

    @mock.patch("djangocms_moderation.admin.notify_collection_moderators")
    @mock.patch("djangocms_moderation.admin.notify_collection_author")
    def test_reject_selected(self, notify_author_mock, notify_moderators_mock):
        # Login as the collection author
        self.client.force_login(self.user)
        data = {
            "action": "reject_selected",
            ACTION_CHECKBOX_NAME: [str(self.root1.pk), str(self.root2.pk)]
        }
        self.assertFalse(self.moderation_request2.is_approved())
        self.assertFalse(self.moderation_request2.is_rejected())
        self.assertTrue(self.moderation_request1.is_approved())

        url = reverse("admin:djangocms_moderation_moderationrequesttreenode_changelist")
        url += "?moderation_request__collection__id={}".format(self.collection.pk)
        response = self.client.post(url, data)
        self.client.post(response.url)

        self.assertFalse(self.moderation_request2.is_approved())
        self.assertTrue(self.moderation_request2.is_rejected())
        self.assertTrue(self.moderation_request1.is_approved())

        self.assertFalse(notify_moderators_mock.called)

        notify_author_mock.assert_called_once_with(
            collection=self.collection,
            moderation_requests=[self.moderation_request2],
            action=self.moderation_request2.get_last_action().action,
            by_user=self.user,
        )

        self.collection.refresh_from_db()
        self.assertEqual(self.collection.status, constants.IN_REVIEW)


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
        self.data = {
            "action": "publish_selected",
            ACTION_CHECKBOX_NAME: [str(self.root1.pk), str(self.root2.pk)]
        }
        self.url = reverse("admin:djangocms_moderation_moderationrequesttreenode_changelist")
        self.url += "?moderation_request__collection__id={}".format(self.collection.pk)

        # Asserts to check data set up is ok. Ideally wouldn't need them, but
        # the set up is so complex that it's safer to have them.
        self.assertTrue(self.moderation_request1.is_active)
        self.assertTrue(self.moderation_request2.is_active)
        self.assertEqual(self.moderation_request1.version.state, DRAFT)
        self.assertEqual(self.moderation_request2.version.state, DRAFT)

    @mock.patch("django.contrib.messages.success")
    def test_publish_selected_publishes_approved_request(self, messages_mock):
        # Select the publish action from the menu
        response = self.client.post(self.url, self.data)
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

    @mock.patch("django.contrib.messages.success")
    def test_publish_selected_sets_collection_to_archived_if_all_requests_published(self, messages_mock):
        # Make sure both moderation requests have been approved
        self.moderation_request2.update_status(constants.ACTION_APPROVED, self.role1.user)
        self.moderation_request2.update_status(constants.ACTION_APPROVED, self.role2.user)

        # Select the publish action from the menu
        response = self.client.post(self.url, self.data)
        # And now go to the view the action redirects to
        response = self.client.post(response.url)

        # Response is correct
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, self.url)
        self.assertEqual(messages_mock.call_args[0][1], '2 requests successfully published')

        # Check approved request was published and started request was not
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

        # Collection still in review as version2 is still draft
        self.collection.refresh_from_db()
        self.assertEqual(self.collection.status, constants.ARCHIVED)

    def test_publish_selected_view_when_using_get(self):
        # Choose the publish_selected action from the dropdown
        response = self.client.post(self.url, self.data)
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
        response = self.client.post(self.url, self.data)

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

        # Set up the url data
        self.data = {
            "action": "resubmit_selected",
            ACTION_CHECKBOX_NAME: [str(self.root1.pk), str(self.root2.pk)]
        }
        self.url = reverse("admin:djangocms_moderation_moderationrequesttreenode_changelist")
        self.url += "?moderation_request__collection__id={}".format(self.collection.pk)

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
        response = self.client.post(self.url, self.data)
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
        response = self.client.post(self.url, self.data)
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
        response = self.client.post(self.url, self.data)

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

    @mock.patch.object(ModerationRequestTreeAdmin, "has_delete_permission", mock.Mock(return_value=True))
    def test_delete_selected_action_cannot_be_accessed_if_not_collection_author(self):
        # Login as a user who is not the collection author
        self.client.force_login(self.get_superuser())
        # Set up action url
        url = reverse("admin:djangocms_moderation_moderationrequesttreenode_changelist")
        url += "?moderation_request__collection__id={}".format(self.collection.pk)

        # Choose the delete_selected action from the dropdown
        data = {
            "action": "delete_selected",
            ACTION_CHECKBOX_NAME: [str(self.root1.pk), str(self.root2.pk)]
        }
        response = self.client.post(url, data)

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
        url = reverse("admin:djangocms_moderation_moderationrequesttreenode_changelist")
        url += "?moderation_request__collection__id={}".format(self.collection.pk)
        data = {
            "action": "delete_selected",
            ACTION_CHECKBOX_NAME: [str(self.root1.pk), str(self.root2.pk)]
        }

        response = self.client.post(url, data)

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

    @mock.patch.object(ModerationRequestTreeAdmin, "has_delete_permission", mock.Mock(return_value=True))
    @mock.patch("djangocms_moderation.admin.notify_collection_moderators")
    @mock.patch("djangocms_moderation.admin.notify_collection_author")
    def test_delete_selected_deletes_all_relevant_objects(self, notify_author_mock, notify_moderators_mock):
        """The selected ModerationRequest and ModerationRequestTreeNode objects should be deleted."""
        # Login as the collection author
        self.client.force_login(self.user)
        # Choose the delete_selected action from the dropdown
        url = reverse("admin:djangocms_moderation_moderationrequesttreenode_changelist")
        url += "?moderation_request__collection__id={}".format(self.collection.pk)
        data = {
            "action": "delete_selected",
            ACTION_CHECKBOX_NAME: [str(self.root1.pk), str(self.root2.pk)]
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, 302)

        # Now do the request the delete_selected action has led us to
        response = self.client.post(response.url)
        self.assertRedirects(response, url)
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
        self.url += "?moderation_request__collection__id={}".format(self.collection.pk)
        self.data = {
            "action": "delete_selected",
            ACTION_CHECKBOX_NAME: [str(self.root1.pk), str(self.root2.pk)]
        }

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
