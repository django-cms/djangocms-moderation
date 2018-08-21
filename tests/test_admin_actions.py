import mock

from django.contrib.admin import ACTION_CHECKBOX_NAME
from django.urls import reverse

from cms.api import create_page

from djangocms_moderation import constants
from djangocms_moderation.admin import ModerationRequestAdmin
from djangocms_moderation.models import (
    ModerationCollection,
    ModerationRequest,
    Workflow,
)

from .utils.base import BaseTestCase


class AdminActionTest(BaseTestCase):

    def setUp(self):
        self.wf = Workflow.objects.create(name='Workflow Test',)
        self.collection = ModerationCollection.objects.create(
            author=self.user, name='Collection Admin Actions', workflow=self.wf, status=constants.IN_REVIEW
        )

        pg1 = create_page(title='Page 1', template='page.html', language='en',)
        pg2 = create_page(title='Page 2', template='page.html', language='en',)

        self.mr1 = ModerationRequest.objects.create(
            content_object=pg1, language='en',  collection=self.collection, is_active=True,)

        self.wfst = self.wf.steps.create(role=self.role1, is_required=True, order=1,)

        # this moderation request is approved
        self.mr1.actions.create(by_user=self.user, action=constants.ACTION_STARTED,)
        self.mr1.actions.create(
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

        self.client.force_login(self.user)

    @mock.patch.object(ModerationRequestAdmin, 'has_delete_permission')
    def test_delete_selected(self, mock_has_delete_permission):
        mock_has_delete_permission.return_value = True
        self.assertEqual(ModerationRequest.objects.filter(collection=self.collection).count(), 2)

        fixtures = [self.mr1, self.mr2]
        data = {
            'action': 'delete_selected',
            ACTION_CHECKBOX_NAME: [str(f.pk) for f in fixtures]
        }
        # This user is not the collection author
        self.client.force_login(self.user2)
        response = self.client.post(self.url_with_filter, data)
        self.assertEqual(response.status_code, 403)
        # Nothing is deleted
        self.assertEqual(ModerationRequest.objects.filter(collection=self.collection).count(), 2)

        # Now lets try with collection author, but without delete permission
        mock_has_delete_permission.return_value = False
        self.client.force_login(self.user)
        response = self.client.post(self.url_with_filter, data)
        self.assertEqual(response.status_code, 403)
        # Nothing is deleted
        self.assertEqual(ModerationRequest.objects.filter(collection=self.collection).count(), 2)

        mock_has_delete_permission.return_value = True
        self.client.force_login(self.user)
        response = self.client.post(self.url_with_filter, data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(ModerationRequest.objects.filter(collection=self.collection).count(), 0)

    @mock.patch('djangocms_moderation.admin_actions.publish_content_object')
    def test_publish_selected(self, mock_publish_content_object):

        fixtures = [self.mr1, self.mr2]
        data = {
            'action': 'publish_selected',
            'select_across': 0,
            'index': 0,
            ACTION_CHECKBOX_NAME: [str(f.pk) for f in fixtures]
        }
        self.client.post(self.url_with_filter, data, follow=True)
        self.assertTrue(self.mr1.is_approved())
        self.assertFalse(self.mr2.is_approved())

        assert mock_publish_content_object.called
        # check it has been called only once, i.e. with the approved mr1
        mock_publish_content_object.assert_called_once_with(self.mr1.content_object)
