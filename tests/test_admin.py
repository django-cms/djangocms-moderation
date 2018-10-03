from django.contrib import admin
from django.contrib.auth.models import Permission, User
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse

from djangocms_versioning.test_utils import factories

from djangocms_moderation import conf, constants
from djangocms_moderation.admin import (
    ModerationCollectionAdmin,
    ModerationRequestAdmin,
)
from djangocms_moderation.constants import ACTION_REJECTED
from djangocms_moderation.models import (
    ModerationCollection,
    ModerationRequest,
    Workflow,
)

from .utils.base import BaseTestCase, MockRequest


class ModerationAdminTestCase(BaseTestCase):
    def setUp(self):
        self.wf = Workflow.objects.create(name='Workflow Test',)
        self.collection = ModerationCollection.objects.create(
            author=self.user, name='Collection Admin Actions', workflow=self.wf, status=constants.IN_REVIEW
        )

        pg1_version = factories.PageVersionFactory()
        pg2_version = factories.PageVersionFactory()

        self.mr1 = ModerationRequest.objects.create(
            version=pg1_version, language='en',  collection=self.collection,
            is_active=True, author=self.collection.author,)

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
            version=pg2_version, language='en',  collection=self.collection,
            is_active=True, author=self.collection.author,)
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

    def test_publish_selected_action_visibility_when_version_is_published(self):
        mock_request = MockRequest()
        mock_request.user = self.user
        mock_request._collection = self.collection

        actions = self.mra.get_actions(request=mock_request)
        # mr1 request is approved so user can see the publish_selected action
        self.assertIn('publish_selected', actions)

        # Now, when version becomes published, they shouldn't see it
        self.mr1.version._set_publish(self.user)
        self.mr1.version.save()
        actions = self.mra.get_actions(request=mock_request)
        self.assertNotIn('publish_selected', actions)

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
        user = User.objects.create(
            username='change_author', email='change_author@test.com', password='can_change_author',)

        mock_request = MockRequest()
        mock_request.user = user
        mock_request._collection = self.collection

        # login
        self.client.force_login(mock_request.user)

        # add the permission
        content_type = ContentType.objects.get_for_model(ModerationCollection)
        permission = Permission.objects.get(content_type=content_type, codename='can_change_author')
        mock_request.user.user_permissions.add(permission)

        # test ModerationRequests
        conf.REQUEST_COMMENTS_ENABLED = False
        list_display = self.mra.get_list_display(mock_request)
        self.assertNotIn('get_comments_link', list_display)

        conf.REQUEST_COMMENTS_ENABLED = True
        list_display = self.mra.get_list_display(mock_request)
        self.assertIn('get_comments_link', list_display)

        # test ModerationCollections
        conf.COLLECTION_COMMENTS_ENABLED = False
        mca_buttons = []
        for action in self.mca.get_list_display_actions():
            mca_buttons.append(action.__name__)
        list_display = self.mca.get_list_display_actions()
        self.assertNotIn('get_comments_link', mca_buttons)

        conf.COLLECTION_COMMENTS_ENABLED = True
        mca_buttons = []
        for action in self.mca.get_list_display_actions():
            mca_buttons.append(action.__name__)
        list_display = self.mca.get_list_display_actions()
        self.assertIn('get_comments_link', mca_buttons)

    def test_change_moderation_collection_author_permission(self):
        user = factories.UserFactory(
            username='change_author',
            email='change_author@test.com',
            password='can_change_author',
            is_staff=True,
            is_active=True,
        )
        mock_request = MockRequest()
        mock_request.user = user
        mock_request._collection = self.collection
        self.client.force_login(mock_request.user)

        # check that the user does not have the permissions
        self.assertFalse(mock_request.user.has_perm('djangocms_moderation.can_change_author'))

        # check that author is readonly
        self.assertIn('author', self.mca.get_readonly_fields(mock_request, self.collection))

        # add the permission
        content_type = ContentType.objects.get_for_model(ModerationCollection)
        permission = Permission.objects.get(content_type=content_type, codename='can_change_author')
        mock_request.user.user_permissions.add(permission)

        # reload the user to clear permissions cache
        user = User.objects.get(pk=user.pk)
        mock_request.user = user

        # test that the permission was added successfully
        self.assertTrue(mock_request.user.has_perm('djangocms_moderation.can_change_author'))

        # check that author is editable
        self.assertNotIn('author', self.mca.get_readonly_fields(mock_request, self.collection))

    def test_get_readonly_fields_for_moderation_collection(self):
        self.assertNotEqual(self.collection.author, self.user3)
        self.collection.status = constants.COLLECTING
        self.collection.save()

        mock_request_author = MockRequest()
        mock_request_author.user = self.collection.author

        mock_request_non_author = MockRequest()
        mock_request_non_author.user = self.user3

        # We are creating a new collection, only `status` should be read_only
        fields = self.mca.get_readonly_fields(mock_request_author)
        self.assertListEqual(['status'], fields)

        # Now we pass the object.
        # The author field will be editable because this is a superuser
        # (it wouldn't be if they weren't and didn't have the 'can_change_author' permission)
        # As the collection is still in `collecting` status and the request
        # user is the author of the collection, they can change still
        # change the `workflow`
        fields = self.mca.get_readonly_fields(mock_request_author, self.collection)
        self.assertListEqual(['status'], fields)

        # Non-author can't edit the workflow
        fields = self.mca.get_readonly_fields(mock_request_non_author, self.collection)
        self.assertListEqual(['status', 'workflow'], fields)

        # If the collection is not in `collecting` status, then the author
        # can't edit the workflow anymore
        self.collection.status = constants.IN_REVIEW
        self.collection.save()
        fields = self.mca.get_readonly_fields(mock_request_author, self.collection)
        self.assertListEqual(['status', 'workflow'], fields)

        fields = self.mca.get_readonly_fields(mock_request_non_author, self.collection)
        self.assertListEqual(['status', 'workflow'], fields)
