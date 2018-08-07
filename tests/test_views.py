import mock

from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils.translation import ugettext_lazy as _

from cms.utils.urlutils import add_url_parameters

from djangocms_moderation.forms import CollectionItemForm
from djangocms_moderation.models import ModerationCollection, ModerationRequest
from djangocms_moderation.utils import get_admin_url

from .utils.base import BaseViewTestCase


class CollectionItemViewTest(BaseViewTestCase):

    def setUp(self):

        self.user = User.objects.create_user(
            username='test1', email='test1@test.com', password='test1', is_staff=True
        )

        self.collection_1 = ModerationCollection.objects.create(
            author=self.user, name='My collection 1', workflow=self.wf1
        )
        self.collection_2 = ModerationCollection.objects.create(
            author=self.user, name='My collection 2', workflow=self.wf1
        )

    def _assert_render(self, response):
        form = response.context_data['form']

        self.assertIsInstance(form, CollectionItemForm)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.template_name[0], 'djangocms_moderation/item_to_collection.html')

        self.assertEqual(response.context_data['title'], _('Add to collection'))

    def test_no_collections(self):
        ModerationCollection.objects.all().delete()
        self.client.force_login(self.user)
        response = self.client.get(
            get_admin_url(
                name='cms_moderation_item_to_collection',
                language='en',
                args=()
            )
        )

        self._assert_render(response)
        self.assertEqual(list(response.context_data['collection_list']), [])

    def test_collections(self):
        self.client.force_login(self.user)
        response = self.client.get(
            get_admin_url(
                name='cms_moderation_item_to_collection',
                language='en',
                args=()
            )
        )

        self._assert_render(response)
        self.assertTrue(self.collection_1 in response.context_data['collection_list'])
        self.assertTrue(self.collection_2 in response.context_data['collection_list'])
        self.assertTrue(2, len(response.context_data['collection_list']))

    def test_add_object_to_collections(self):
        ModerationRequest.objects.all().delete()
        self.client.force_login(self.user)
        response = self.client.post(
            get_admin_url(
                name='cms_moderation_item_to_collection',
                language='en',
                args=()
            ), {'collection_id':  self.collection_1.pk, 'content_object_id': self.pg1.pk})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'reloadBrowser')

        content_type = ContentType.objects.get_for_model(self.pg1)
        moderation_request = ModerationRequest.objects.filter(
            content_type=content_type,
            object_id=self.pg1.pk,
        )[0]

        self.assertEqual(moderation_request.collection, self.collection_1)

    def test_invalid_content_already_in_collection(self):
        # add object
        self.collection_1._add_object(self.pg1)

        self.client.force_login(self.user)
        response = self.client.post(
            get_admin_url(
                name='cms_moderation_item_to_collection',
                language='en',
                args=()
            ), {'collection_id': self.collection_1.pk, 'content_object_id': self.pg1.pk})

        self.assertEqual(response.status_code, 200)
        self.assertTrue('content_object_id' in response.context_data['form'].errors.keys())
        self.assertIn(
              "is already part of existing moderation request which is part",
              response.context_data['form'].errors['content_object_id'][0]
        )

    def test_non_existing_content_object(self):
        self.client.force_login(self.user)
        response = self.client.post(
            get_admin_url(
                name='cms_moderation_item_to_collection',
                language='en',
                args=()
            ), {'collection_id': self.collection_1.pk, 'content_object_id': 9000})

        self.assertEqual(response.status_code, 200)

        self.assertEqual(
            _('Invalid content_object_id, does not exist'),
            response.context_data['form'].errors['content_object_id'][0]
        )

    def test_exclude_locked_collections(self):
        ModerationRequest.objects.all().delete()
        self.collection_1.is_locked = True
        self.collection_1.save()

        self.client.force_login(self.user)
        response = self.client.post(
            get_admin_url(
                name='cms_moderation_item_to_collection',
                language='en',
                args=()
            ), {'collection_id': self.collection_1.pk, 'content_object_id': self.pg1.pk})

        self.assertEqual(
            "Can't add the object to the collection, because it is locked",
            response.context_data['form'].errors['collection_id'][0]
        )

    def test_list_content_objects_from_first_collection(self):
        ModerationRequest.objects.all().delete()

        collections = ModerationCollection.objects.filter(is_locked=False)
        collections[0]._add_object(self.pg1)
        collections[1]._add_object(self.pg2)

        self.client.force_login(self.user)
        response = self.client.get(
            get_admin_url(
                name='cms_moderation_item_to_collection',
                language='en',
                args=()
            )
        )

        moderation_requests = ModerationRequest.objects.filter(collection=collections[0])
        # moderation request is content_object
        for mod_request in moderation_requests:
            self.assertTrue(mod_request in response.context_data['content_object_list'])

    def test_list_content_objects_from_collection_id_param(self):
        ModerationRequest.objects.all().delete()

        self.collection_1._add_object(self.pg1)
        self.collection_2._add_object(self.pg2)

        self.client.force_login(self.user)
        response = self.client.get(
            add_url_parameters(
                get_admin_url(
                    name='cms_moderation_item_to_collection',
                    language='en',
                    args=()
                ), collection_id=self.collection_2.pk
            )
        )

        moderation_requests = ModerationRequest.objects.filter(collection=self.collection_2)
        # moderation request is content_object
        for mod_request in moderation_requests:
            self.assertTrue(mod_request in response.context_data['content_object_list'])

    def test_content_object_id_from_params(self):
        self.client.force_login(self.user)
        response = self.client.get(
            add_url_parameters(
                get_admin_url(
                    name='cms_moderation_item_to_collection',
                    language='en',
                    args=()
                ), content_object_id=self.pg1.pk
            )
        )

        form = response.context_data['form']
        self.assertEqual(self.pg1.pk, int(form.initial['content_object_id']))

    def test_authenticated_users_only(self):
        response = self.client.get(
            get_admin_url(
                name='cms_moderation_item_to_collection',
                language='en',
                args=()
            )
        )

        self.assertEqual(response.status_code, 302)


class SubmitCollectionForModerationViewTest(BaseViewTestCase):
    def setUp(self):
        super(SubmitCollectionForModerationViewTest, self).setUp()
        self.url = reverse(
            'admin:cms_moderation_submit_collection_for_moderation',
            args=(self.collection2.pk,)
        )
        request_change_list_url = reverse('admin:djangocms_moderation_moderationrequest_changelist')
        self.request_change_list_url = "{}?collection__id__exact={}".format(
            request_change_list_url,
            self.collection2.pk
        )

    @mock.patch.object(ModerationCollection, 'submit_for_moderation')
    def test_submit_collection_for_moderation(self, submit_mock):
        response = self.client.get(self.url)
        self.assertEqual(200, response.status_code)

        response = self.client.post(self.url)
        assert submit_mock.called
        self.assertEqual(302, response.status_code)
        self.assertEqual(self.request_change_list_url, response.url)


class ModerationRequestChangeListView(BaseViewTestCase):
    def setUp(self):
        super(ModerationRequestChangeListView, self).setUp()
        self.collection_submit_url = reverse(
            'admin:cms_moderation_submit_collection_for_moderation',
            args=(self.collection2.pk,)
        )
        self.url = reverse('admin:djangocms_moderation_moderationrequest_changelist')
        self.url_with_filter = "{}?collection__id__exact={}".format(
            self.url, self.collection2.pk
        )

    def test_change_list_view_should_contain_collection_object(self):
        response = self.client.get(self.url)
        self.assertEqual(200, response.status_code)
        self.assertNotIn('collection', response.context)

        response = self.client.get(self.url_with_filter)
        self.assertEqual(200, response.status_code)
        self.assertEqual(response.context['collection'], self.collection2)

    @mock.patch.object(ModerationCollection, 'allow_submit_for_moderation')
    def test_change_list_view_should_contain_submit_collection_url(self, allow_submit_mock):
        response = self.client.get(self.url)
        self.assertEqual(200, response.status_code)
        self.assertNotIn('submit_for_moderation_url', response.context)

        allow_submit_mock.__get__ = mock.Mock(return_value=False)
        response = self.client.get(self.url_with_filter)
        self.assertNotIn('submit_for_moderation_url', response.context)

        allow_submit_mock.__get__ = mock.Mock(return_value=True)
        response = self.client.get(self.url_with_filter)
        self.assertIn('submit_for_moderation_url', response.context)

