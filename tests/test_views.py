import mock

from django.contrib.messages import get_messages
from django.urls import reverse

from cms.utils.urlutils import add_url_parameters

from djangocms_versioning.test_utils.factories import PageVersionFactory

from djangocms_moderation.models import ModerationCollection, ModerationRequest
from djangocms_moderation.utils import get_admin_url

from .utils.base import BaseViewTestCase


class CollectionItemsViewTest(BaseViewTestCase):
    def setUp(self):
        super().setUp()
        self.client.force_login(self.user)

    def test_no_eligible_items_to_add_to_collection(self):
        """
        We try add pg4_version to a collection but expect it to fail
        as it is already party of a collection
        """
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

    def test_add_items_to_collection_no_return_url_set(self):
        ModerationRequest.objects.all().delete()
        pg_version = PageVersionFactory(created_by=self.user)

        url = add_url_parameters(
            get_admin_url(
                name='cms_moderation_items_to_collection',
                language='en',
                args=()
            ),
            # not return url specified
            version_ids=pg_version.pk,
            collection_id=self.collection1.pk
        )
        response = self.client.post(
            path=url,
            data={
                'collection': self.collection1.pk,
                'versions': [pg_version.pk],
            },
            follow=False
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'reloadBrowser')

        self.assertTrue(
            ModerationRequest.objects.filter(
                version=pg_version, collection=self.collection1
            ).exists()
        )

    def test_add_items_to_collection_return_url_set(self):
        ModerationRequest.objects.all().delete()
        pg1_version = PageVersionFactory(created_by=self.user)
        pg2_version = PageVersionFactory(created_by=self.user)

        redirect_to_url = reverse('admin:djangocms_moderation_moderationcollection_changelist')

        url = add_url_parameters(
            get_admin_url(
                name='cms_moderation_items_to_collection',
                language='en',
                args=()
            ),
            return_to_url=redirect_to_url,
            version_ids=','.join(str(x) for x in [pg1_version.pk, pg2_version.pk]),
            collection_id=self.collection1.pk
        )
        response = self.client.post(
            path=url,
            data={
                'collection': self.collection1.pk,
                'versions': [pg1_version.pk, pg2_version.pk],
            },
            follow=False
        )

        self.assertRedirects(response, redirect_to_url)

        moderation_request = ModerationRequest.objects.get(version=pg1_version)
        self.assertEqual(moderation_request.collection, self.collection1)

        moderation_request = ModerationRequest.objects.get(version=pg1_version)
        self.assertEqual(moderation_request.collection, self.collection1)

        messages = list(get_messages(response.wsgi_request))
        self.assertIn(
            '2 items successfully added to moderation collection',
            [message.message for message in messages]
        )

    def test_list_versions_from_collection_id_param(self):
        ModerationRequest.objects.all().delete()

        collection1 = ModerationCollection.objects.create(
            author=self.user, name='My collection 1', workflow=self.wf1
        )
        collection2 = ModerationCollection.objects.create(
            author=self.user, name='My collection 2', workflow=self.wf1
        )

        pg1_version = PageVersionFactory(created_by=self.user)
        pg2_version = PageVersionFactory(created_by=self.user)

        collection1.add_version(pg1_version)
        collection2.add_version(pg2_version)

        new_version = PageVersionFactory(created_by=self.user)
        url = add_url_parameters(
            get_admin_url(
                name='cms_moderation_items_to_collection',
                language='en',
                args=()
            ),
            return_to_url='http://example.com',
            version_ids=new_version.pk,
            collection_id=collection1.pk
        )

        response = self.client.get(url)
        mr1 = ModerationRequest.objects.get(version=pg1_version, collection=collection1)
        mr2 = ModerationRequest.objects.get(version=pg2_version, collection=collection2)
        # mr1 is in the list as it belongs to collection1
        self.assertIn(mr1, response.context_data['moderation_request_list'])
        self.assertNotIn(mr2, response.context_data['moderation_request_list'])


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
