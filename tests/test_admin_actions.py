import mock

from django.contrib.admin import ACTION_CHECKBOX_NAME
from django.urls import reverse

from djangocms_moderation import constants
from djangocms_moderation.admin import ModerationRequestAdmin
from djangocms_moderation.constants import ACTION_REJECTED
from djangocms_moderation.models import (
    ModerationCollection,
    ModerationRequest,
    Role,
    Workflow,
)
from djangocms_versioning.test_utils.factories import PageVersionFactory

from .utils.base import BaseTestCase


class AdminActionTest(BaseTestCase):

    def setUp(self):
        self.wf = Workflow.objects.create(name='Workflow Test',)
        self.collection = ModerationCollection.objects.create(
            author=self.user,
            name='Collection Admin Actions',
            workflow=self.wf,
            status=constants.IN_REVIEW,
        )

        pg1_version = PageVersionFactory()
        pg2_version = PageVersionFactory()

        self.mr1 = ModerationRequest.objects.create(
            version=pg1_version, language='en',  collection=self.collection, is_active=True,)

        self.wfst1 = self.wf.steps.create(role=self.role1, is_required=True, order=1,)
        self.wfst2 = self.wf.steps.create(role=self.role2, is_required=True, order=1,)

        # this moderation request is approved
        self.mr1.actions.create(by_user=self.user, action=constants.ACTION_STARTED,)
        self.mr1.update_status(constants.ACTION_APPROVED, self.user)
        self.mr1.update_status(constants.ACTION_APPROVED, self.user2)

        # this moderation request is not approved
        self.mr2 = ModerationRequest.objects.create(
            version=pg2_version, language='en',  collection=self.collection, is_active=True,)
        self.mr2.actions.create(by_user=self.user, action=constants.ACTION_STARTED,)

        self.url = reverse('admin:djangocms_moderation_moderationrequest_changelist')
        self.url_with_filter = "{}?collection__id__exact={}".format(
            self.url, self.collection.pk
        )

        self.client.force_login(self.user)

    @mock.patch.object(ModerationRequestAdmin, 'has_delete_permission')
    @mock.patch('djangocms_moderation.admin_actions.notify_collection_moderators')
    @mock.patch('djangocms_moderation.admin_actions.notify_collection_author')
    def test_delete_selected(self, notify_author_mock, notify_moderators_mock, mock_has_delete_permission):
        mock_has_delete_permission.return_value = True
        self.assertEqual(ModerationRequest.objects.filter(collection=self.collection).count(), 2)

        fixtures = [self.mr1, self.mr2]
        data = {
            'action': 'delete_selected',
            ACTION_CHECKBOX_NAME: [str(f.pk) for f in fixtures]
        }
        # This user is not the collection author
        self.client.force_login(self.user2)
        self.client.post(self.url_with_filter, data)
        # Nothing is deleted
        self.assertEqual(ModerationRequest.objects.filter(collection=self.collection).count(), 2)

        # Now lets try with collection author, but without delete permission
        mock_has_delete_permission.return_value = False
        self.client.force_login(self.user)
        response = self.client.post(self.url_with_filter, data)
        self.assertEqual(response.status_code, 403)
        # Nothing is deleted
        self.assertEqual(ModerationRequest.objects.filter(collection=self.collection).count(), 2)

        self.collection.refresh_from_db()
        self.assertEqual(self.collection.status, constants.IN_REVIEW)

        mock_has_delete_permission.return_value = True
        self.client.force_login(self.user)
        response = self.client.post(self.url_with_filter, data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(ModerationRequest.objects.filter(collection=self.collection).count(), 0)

        notify_author_mock.assert_called_once_with(
            collection=self.collection,
            moderation_requests=[self.mr1, self.mr2],
            action=constants.ACTION_CANCELLED,
            by_user=self.user,
        )

        self.assertFalse(notify_moderators_mock.called)

        # All moderation requests were deleted, so collection should be archived
        self.collection.refresh_from_db()
        self.assertEqual(self.collection.status, constants.ARCHIVED)

    @mock.patch('djangocms_moderation.admin_actions.publish_version')
    def test_publish_selected(self, mock_publish_version):
        fixtures = [self.mr1, self.mr2]
        data = {
            'action': 'publish_selected',
            ACTION_CHECKBOX_NAME: [str(f.pk) for f in fixtures]
        }
        self.client.post(self.url_with_filter, data, follow=True)

        assert mock_publish_version.called
        # check it has been called only once, i.e. with the approved mr1
        mock_publish_version.assert_called_once_with(self.mr1.version)

    @mock.patch('djangocms_moderation.admin_actions.notify_collection_moderators')
    @mock.patch('djangocms_moderation.admin_actions.notify_collection_author')
    def test_approve_selected(self, notify_author_mock, notify_moderators_mock):
        fixtures = [self.mr1, self.mr2]
        data = {
            'action': 'approve_selected',
            ACTION_CHECKBOX_NAME: [str(f.pk) for f in fixtures]
        }
        self.assertFalse(self.mr2.is_approved())
        self.assertTrue(self.mr1.is_approved())

        self.client.post(self.url_with_filter, data)

        notify_author_mock.assert_called_once_with(
            collection=self.collection,
            moderation_requests=[self.mr2],
            action=self.mr2.get_last_action().action,
            by_user=self.user,
        )

        notify_moderators_mock.assert_called_once_with(
            collection=self.collection,
            moderation_requests=[self.mr2],
            action_obj=self.mr2.get_last_action(),
        )
        notify_author_mock.reset_mock()
        notify_moderators_mock.reset_mock()

        # There are 2 steps so we need to approve both to get mr2 approved
        self.assertFalse(self.mr2.is_approved())
        self.assertTrue(self.mr1.is_approved())
        self.collection.refresh_from_db()
        self.assertEqual(self.collection.status, constants.IN_REVIEW)

        self.client.force_login(self.user2)
        self.client.post(self.url_with_filter, data)

        self.assertTrue(self.mr2.is_approved())
        self.assertTrue(self.mr1.is_approved())
        self.collection.refresh_from_db()
        self.assertEqual(self.collection.status, constants.ARCHIVED)

        notify_author_mock.assert_called_once_with(
            collection=self.collection,
            moderation_requests=[self.mr2],
            action=self.mr2.get_last_action().action,
            by_user=self.user2,
        )
        self.assertFalse(notify_moderators_mock.called)

    @mock.patch('djangocms_moderation.admin_actions.notify_collection_moderators')
    @mock.patch('djangocms_moderation.admin_actions.notify_collection_author')
    def test_reject_selected(self, notify_author_mock, notify_moderators_mock):
        fixtures = [self.mr1, self.mr2]
        data = {
            'action': 'reject_selected',
            ACTION_CHECKBOX_NAME: [str(f.pk) for f in fixtures]
        }
        self.assertFalse(self.mr2.is_approved())
        self.assertFalse(self.mr2.is_rejected())
        self.assertTrue(self.mr1.is_approved())

        self.client.post(self.url_with_filter, data)

        self.assertFalse(self.mr2.is_approved())
        self.assertTrue(self.mr2.is_rejected())
        self.assertTrue(self.mr1.is_approved())

        self.assertFalse(notify_moderators_mock.called)

        notify_author_mock.assert_called_once_with(
            collection=self.collection,
            moderation_requests=[self.mr2],
            action=self.mr2.get_last_action().action,
            by_user=self.user,
        )

        self.collection.refresh_from_db()
        self.assertEqual(self.collection.status, constants.IN_REVIEW)

    @mock.patch('djangocms_moderation.admin_actions.notify_collection_moderators')
    @mock.patch('djangocms_moderation.admin_actions.notify_collection_author')
    def test_resubmit_selected(self, notify_author_mock, notify_moderators_mock):
        self.mr2.update_status(
            action=ACTION_REJECTED,
            by_user=self.user
        )

        fixtures = [self.mr1, self.mr2]
        data = {
            'action': 'resubmit_selected',
            ACTION_CHECKBOX_NAME: [str(f.pk) for f in fixtures]
        }
        self.assertTrue(self.mr2.is_rejected())
        self.assertTrue(self.mr1.is_approved())

        self.client.post(self.url_with_filter, data)

        self.assertFalse(self.mr2.is_rejected())
        self.assertTrue(self.mr1.is_approved())

        self.assertFalse(notify_author_mock.called)
        notify_moderators_mock.assert_called_once_with(
            collection=self.collection,
            moderation_requests=[self.mr2],
            action_obj=self.mr2.get_last_action(),
        )

        self.collection.refresh_from_db()
        self.assertEqual(self.collection.status, constants.IN_REVIEW)

    @mock.patch('djangocms_moderation.admin_actions.notify_collection_moderators')
    def test_approve_selected_sends_correct_emails(self, notify_moderators_mock):
        role4 = Role.objects.create(user=self.user)
        # Add two more steps
        self.wf.steps.create(role=self.role3, is_required=True, order=1,)
        self.wf.steps.create(role=role4, is_required=True, order=1,)
        self.user.groups.add(self.group)

        # Add one more, partially approved request
        pg3_version = PageVersionFactory()
        self.mr3 = ModerationRequest.objects.create(
            version=pg3_version, language='en',  collection=self.collection, is_active=True,)
        self.mr3.actions.create(by_user=self.user, action=constants.ACTION_STARTED,)
        self.mr3.update_status(by_user=self.user, action=constants.ACTION_APPROVED,)
        self.mr3.update_status(by_user=self.user2, action=constants.ACTION_APPROVED,)

        self.user.groups.add(self.group)

        fixtures = [self.mr1, self.mr2, self.mr3]
        data = {
            'action': 'approve_selected',
            ACTION_CHECKBOX_NAME: [str(f.pk) for f in fixtures]
        }

        # First post as `self.user` should notify mr1 and mr2 and mr3 moderators
        self.client.post(self.url_with_filter, data)
        # The notify email will be send accordingly. As mr1 and mr3 are in the
        # different stages of approval compared to mr 2,
        # we need to send 2 emails to appropriate moderators
        self.assertEqual(notify_moderators_mock.call_count, 2)
        self.assertEqual(
            notify_moderators_mock.call_args_list[0],
            mock.call(collection=self.collection,
                      moderation_requests=[self.mr1, self.mr3],
                      action_obj=self.mr1.get_last_action()
                      )
        )

        self.assertEqual(
            notify_moderators_mock.call_args_list[1],
            mock.call(collection=self.collection,
                      moderation_requests=[self.mr2],
                      action_obj=self.mr2.get_last_action(),
                      )
        )
        self.assertFalse(self.mr1.is_approved())
        self.assertFalse(self.mr3.is_approved())

        notify_moderators_mock.reset_mock()
        self.client.post(self.url_with_filter, data)
        # Second post approves m3 and mr1, but as this is the last stage of
        # the approval, there is no need for notification emails anymore
        self.assertEqual(notify_moderators_mock.call_count, 0)
        self.assertTrue(self.mr1.is_approved())
        self.assertTrue(self.mr3.is_approved())

        self.client.force_login(self.user2)
        # user2 can approve only 1 request, mr2, so one notification email
        # should go out
        self.client.post(self.url_with_filter, data)
        notify_moderators_mock.assert_called_once_with(
            collection=self.collection,
            moderation_requests=[self.mr2],
            action_obj=self.mr2.get_last_action(),
        )

        self.user.groups.remove(self.group)

        # Not all request have been fully approved
        self.collection.refresh_from_db()
        self.assertEqual(self.collection.status, constants.IN_REVIEW)
