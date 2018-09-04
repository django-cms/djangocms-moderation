from django.contrib import admin
from django.urls import reverse

from cms.api import create_page

from djangocms_moderation import conf
from djangocms_moderation import constants
from djangocms_moderation.admin import ModerationRequestAdmin, ModerationCollectionAdmin
from djangocms_moderation.constants import ACTION_REJECTED
from djangocms_moderation.models import (
    ModerationCollection,
    ModerationRequest,
    Workflow,
)

from .utils.base import BaseTestCase


class MockRequest:
    GET = {}


class ModerationAdminTestCase(BaseTestCase):
    def setUp(self):
        self.wf = Workflow.objects.create(name='Workflow Test',)
        self.collection = ModerationCollection.objects.create(
            author=self.user, name='Collection Admin Actions', workflow=self.wf, status=constants.IN_REVIEW
        )

        pg1 = create_page(title='Page 1', template='page.html', language='en',)
        pg2 = create_page(title='Page 2', template='page.html', language='en',)

        self.mr1 = ModerationRequest.objects.create(
            content_object=pg1, language='en',  collection=self.collection, is_active=True,)

        self.wfst = self.wf.steps.create(role=self.role2, is_required=True, order=1,)

        # this moderation request is approved
        self.mr1.actions.create(by_user=self.user, action=constants.ACTION_STARTED,)
        self.mr1action2 = self.mr1.actions.create(
            by_user=self.user,
            to_user=self.user2,
            action=constants.ACTION_APPROVED,
            step_approved=self.wfst,
        )

        # this moderation request is not approved
        self.mr2 = ModerationRequest.objects.create(
            content_object=pg2, language='en',  collection=self.collection, is_active=True,)
        self.mr2.actions.create(by_user=self.user, action=constants.ACTION_STARTED,)

        self.url = reverse('admin:djangocms_moderation_moderationrequest_changelist')
        self.url_with_filter = "{}?collection__id__exact={}".format(
            self.url, self.collection.pk
        )
        self.mra = ModerationRequestAdmin(ModerationRequest, admin.AdminSite())
        self.mca = ModerationCollectionAdmin(ModerationCollection, admin.AdminSite())

    def test_delete_selected_action_visibility(self):
        mock_request = MockRequest()
        mock_request.user = self.user
        mock_request._collection = self.collection
        actions = self.mra.get_actions(request=mock_request)
        self.assertIn('delete_selected', actions)

        # user2 won't be able to delete requests, as they are not the collection
        # author
        mock_request.user = self.user2
        actions = self.mra.get_actions(request=mock_request)
        self.assertNotIn('delete_selected', actions)

    def test_publish_selected_action_visibility(self):
        mock_request = MockRequest()
        mock_request.user = self.user
        mock_request._collection = self.collection
        actions = self.mra.get_actions(request=mock_request)
        # mr1 request is approved, so user1 can see the publish selected option
        self.assertIn('publish_selected', actions)

        # user2 should not be able to see it
        mock_request.user = self.user2
        actions = self.mra.get_actions(request=mock_request)
        self.assertNotIn('publish_selected', actions)

        # if there are no approved requests, user can't see the button either
        mock_request.user = self.user
        self.mr1.get_last_action().delete()
        actions = self.mra.get_actions(request=mock_request)
        self.assertNotIn('publish_selected', actions)

    def test_approve_and_reject_selected_action_visibility(self):
        mock_request = MockRequest()
        mock_request.user = self.user
        mock_request._collection = self.collection
        actions = self.mra.get_actions(request=mock_request)
        # mr1 is not a moderator for collection1 so he can't approve or reject
        # anything
        self.assertNotIn('approve_selected', actions)
        self.assertNotIn('reject_selected', actions)

        # user2 is moderator and there is 1 unapproved request
        mock_request.user = self.user2
        actions = self.mra.get_actions(request=mock_request)
        self.assertIn('approve_selected', actions)
        self.assertIn('reject_selected', actions)

        # now everything is approved, so not even user2 can see the actions
        self.mr2.delete()
        actions = self.mra.get_actions(request=mock_request)
        self.assertNotIn('approve_selected', actions)
        self.assertNotIn('reject_selected', actions)

    def test_resubmit_selected_action_visibility(self):
        mock_request = MockRequest()
        mock_request.user = self.user
        mock_request._collection = self.collection
        actions = self.mra.get_actions(request=mock_request)
        # There is nothing set to re-work, so user can't see the resubmit action
        self.assertNotIn('resubmit_selected', actions)

        self.mr1action2.action = ACTION_REJECTED
        self.mr1action2.save()
        actions = self.mra.get_actions(request=mock_request)
        # There is 1 mr to rework now, so user can do it
        self.assertIn('resubmit_selected', actions)

        # user2 can't, as they are not the author of the request
        mock_request.user = self.user2
        actions = self.mra.get_actions(request=mock_request)
        self.assertNotIn('resubmit_selected', actions)

    def test_in_review_status_is_considered(self):
        mock_request = MockRequest()
        mock_request.user = self.user
        mock_request._collection = self.collection
        self.collection.status = constants.ARCHIVED
        self.collection.save()

        actions = self.mra.get_actions(request=mock_request)
        # for self.user, the publish_selected should be available even if
        # collection status is ARCHIVED
        self.assertIn('publish_selected', actions)

        mock_request.user = self.user2
        actions = self.mra.get_actions(request=mock_request)
        # mr2 request is not approved, so user2 should see the
        # approve_selected option, but the collection is not in IN_REVIEW
        self.assertNotIn('approve_selected', actions)

        self.collection.status = constants.IN_REVIEW
        self.collection.save()
        actions = self.mra.get_actions(request=mock_request)
        self.assertIn('approve_selected', actions)

    def test_change_list_view_should_respect_conf(self):
        mock_request = MockRequest()
        mock_request.user = self.user
        mock_request._collection = self.collection
        conf.COLLECTION_COMMENTS_ENABLED = False
        list_display = self.mca.get_list_display(mock_request)
        self.assertNotIn('get_comments_link', list_display)
        conf.COLLECTION_COMMENTS_ENABLED = True
        list_display = self.mca.get_list_display(mock_request)
        self.assertIn('get_comments_link', list_display)
        conf.REQUEST_COMMENTS_ENABLED = False
        list_display = self.mra.get_list_display(mock_request)
        self.assertNotIn('get_comments_link', list_display)
        conf.REQUEST_COMMENTS_ENABLED = True
        list_display = self.mra.get_list_display(mock_request)
        self.assertIn('get_comments_link', list_display)

