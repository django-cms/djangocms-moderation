import mock
from mock import patch

from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.contrib.messages import get_messages
from django.urls import reverse
from django.utils.translation import ugettext_lazy as _

from cms.utils.urlutils import add_url_parameters

from djangocms_versioning.test_utils.factories import PageVersionFactory

from djangocms_moderation import constants, views
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

        self.content_type = ContentType.objects.get_for_model(self.pg1_version)
        self.pg_version = PageVersionFactory(created_by=self.user)

    def _assert_render(self, response):
        form = response.context_data['form']

        self.assertIsInstance(form, CollectionItemForm)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.template_name[0], 'djangocms_moderation/item_to_collection.html')

        self.assertEqual(response.context_data['title'], _('Add to collection'))

    def test_version_object_to_collections_from_modal(self):
        ModerationRequest.objects.all().delete()
        self.client.force_login(self.user)
        url = add_url_parameters(
            get_admin_url(
                name='cms_moderation_item_to_collection',
                language='en',
                args=()
            ),
            _modal=1,
        )
        response = self.client.post(
            path=url,
            data={
                'collection':  self.collection_1.pk,
                'version': self.pg_version.pk,
            }
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'reloadBrowser')

        moderation_request = ModerationRequest.objects.filter(
            version=self.pg_version,
        )[0]

        self.assertEqual(moderation_request.collection, self.collection_1)

    def test_version_object_to_collections_from_changelist(self):
        ModerationRequest.objects.all().delete()
        self.client.force_login(self.user)
        url = get_admin_url(
            name='cms_moderation_item_to_collection',
            language='en',
            args=()
        )

        with patch.object(views, 'version_list_url') as mock_:
            response = self.client.post(
                path=url,
                data={
                    'collection': self.collection_1.pk,
                    'version': self.pg_version.pk,
                }
            )

        mock_.assert_called_with(self.pg_version.content)
        self.assertEqual(response.status_code, 302)

        moderation_request = ModerationRequest.objects.filter(
            version=self.pg_version,
        )[0]

        self.assertEqual(moderation_request.collection, self.collection_1)

    def test_invalid_version_already_in_collection(self):
        self.collection_1.add_version(self.pg_version)
        self.assertEqual(1, ModerationRequest.objects.filter(version=self.pg_version).count())

        self.client.force_login(self.user)

        response = self.client.post(
            get_admin_url(
                name='cms_moderation_item_to_collection',
                language='en',
                args=()
            ), {'collection': self.collection_2.pk,
                'version': self.pg_version.pk})

        self.assertEqual(response.status_code, 200)
        self.assertIn(
              "is already part of existing moderation request which is part",
              response.context_data['form'].errors['version'][0]
        )
        self.assertEqual(1, ModerationRequest.objects.filter(version=self.pg_version).count())

        # make the moderation request inactive, we will be able to submit it
        self.collection_1.moderation_requests.all().update(is_active=False)
        response = self.client.post(
            get_admin_url(
                name='cms_moderation_item_to_collection',
                language='en',
                args=()
            ), {'collection': self.collection_2.pk,
                'version': self.pg_version.pk})

        self.assertEqual(response.status_code, 302)
        self.assertEqual(2, ModerationRequest.objects.filter(version=self.pg_version).count())

    def test_non_existing_version(self):
        self.client.force_login(self.user)
        response = self.client.post(
            get_admin_url(
                name='cms_moderation_item_to_collection',
                language='en',
                args=()
            ), {'collection': self.collection_1.pk,
                'version': 9000})

        self.assertEqual(response.status_code, 200)
        self.assertIn('version', response.context_data['form'].errors)

    def test_prevent_locked_collections(self):
        """
        from being selected when adding to collection
        """
        ModerationRequest.objects.all().delete()
        self.collection_1.status = constants.IN_REVIEW
        self.collection_1.save()
        self.client.force_login(self.user)
        response = self.client.post(
            get_admin_url(
                name='cms_moderation_item_to_collection',
                language='en',
                args=()
            ), {'collection': self.collection_1.pk, 'version': self.pg1_version.pk})

        # locked collection are not part of the list
        self.assertEqual(
            "Select a valid choice. That choice is not one of the available choices.",
            response.context_data['form'].errors['collection'][0]
        )

    def test_list_versions_from_collection_id_param(self):
        ModerationRequest.objects.all().delete()
        pg2_version = PageVersionFactory()

        self.collection_1.add_version(self.pg_version)
        self.collection_2.add_version(pg2_version)

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
            self.assertTrue(mod_request in response.context_data['moderation_request_list'])

    def test_version_id_from_params(self):
        self.client.force_login(self.user)
        response = self.client.get(
            add_url_parameters(
                get_admin_url(
                    name='cms_moderation_item_to_collection',
                    language='en',
                    args=()
                ), version_id=self.pg1_version.pk
            )
        )

        form = response.context_data['form']
        self.assertEqual(self.pg1_version.pk, int(form.initial['version']))

    def test_authenticated_users_only(self):
        response = self.client.get(
            get_admin_url(
                name='cms_moderation_item_to_collection',
                language='en',
                args=()
            )
        )

        self.assertEqual(response.status_code, 302)


class CollectionItemsViewTest(BaseViewTestCase):
    def test_no_suitable_items_to_add_to_collection(self):
        """
        We try add pg4_version to a collection but expect it to fail as it is already party of a collection
        """
        self.client.force_login(self.user)
        url = add_url_parameters(
            get_admin_url(
                name='cms_moderation_items_to_collection',
                language='en',
                args=()
            ),
            return_to_url='http://example.com',
            version_ids=self.pg4_version.pk,
            collection_id=self.collection1.pk
        )
        response = self.client.post(
            path=url,
            data={
                'collection': self.collection1.pk,
                'versions': self.pg4_version.pk,
            },
            follow=False
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn('versions', response.context['form'].errors)

    def test_add_items_to_collection(self):
        pg_version1 = PageVersionFactory(created_by=self.user)
        pg_version2 = PageVersionFactory(created_by=self.user)
        ModerationRequest.objects.all().delete()
        self.client.force_login(self.user)

        url = add_url_parameters(
            get_admin_url(
                name='cms_moderation_items_to_collection',
                language='en',
                args=()
            ),
            return_to_url='http://example.com',
            version_ids=','.join(str(x) for x in [pg_version1.pk, pg_version2.pk]),
            collection_id=self.collection1.pk
        )
        response = self.client.post(
            path=url,
            data={
                'collection': self.collection1.pk,
                'versions': [pg_version1.pk, pg_version2.pk],
            },
            follow=False
        )

        self.assertEqual(response.status_code, 302)

        moderation_request = ModerationRequest.objects.get(version=pg_version1)
        self.assertEqual(moderation_request.collection, self.collection1)

        moderation_request = ModerationRequest.objects.get(version=pg_version1)
        self.assertEqual(moderation_request.collection, self.collection1)

        messages = list(get_messages(response.wsgi_request))
        self.assertTrue(
            '2 items successfully added to moderation collection' in [message.message for message in messages])


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

    @mock.patch.object(ModerationCollection, 'submit_for_review')
    def test_submit_collection_for_moderation(self, submit_mock):
        response = self.client.get(self.url)
        self.assertEqual(200, response.status_code)

        response = self.client.post(self.url)
        assert submit_mock.called
        self.assertEqual(302, response.status_code)
        self.assertEqual(self.request_change_list_url, response.url)


class CancelCollectionViewTest(BaseViewTestCase):
    def setUp(self):
        super().setUp()
        self.url = reverse(
            'admin:cms_moderation_cancel_collection',
            args=(self.collection2.pk,)
        )
        self.collection_change_list_url = reverse('admin:djangocms_moderation_moderationcollection_changelist')

    @mock.patch.object(ModerationCollection, 'cancel')
    def test_submit_collection_for_moderation(self, cancel_mock):
        response = self.client.get(self.url)
        self.assertEqual(200, response.status_code)

        response = self.client.post(self.url)
        assert cancel_mock.called
        self.assertEqual(302, response.status_code)
        self.assertEqual(self.collection_change_list_url, response.url)


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

    def test_change_list_view_should_404_if_not_filtered(self):
        response = self.client.get(self.url)
        self.assertEqual(404, response.status_code)

        response = self.client.get(self.url_with_filter)
        self.assertEqual(200, response.status_code)

    def test_change_list_view_should_contain_collection_object(self):
        response = self.client.get(self.url_with_filter)
        self.assertEqual(200, response.status_code)
        self.assertEqual(response.context['collection'], self.collection2)

    @mock.patch.object(ModerationCollection, 'allow_submit_for_review')
    def test_change_list_view_should_contain_submit_collection_url(self, allow_submit_mock):
        allow_submit_mock.return_value = False
        response = self.client.get(self.url_with_filter)
        self.assertNotIn('submit_for_review_url', response.context)

        allow_submit_mock.return_value = True
        response = self.client.get(self.url_with_filter)
        self.assertIn('submit_for_review_url', response.context)
