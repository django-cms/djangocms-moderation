import mock

from django.contrib.admin import ACTION_CHECKBOX_NAME
from django.contrib.messages import get_messages
from django.urls import reverse

from cms.utils.urlutils import add_url_parameters

from djangocms_versioning.test_utils.factories import PageVersionFactory

from djangocms_moderation.models import (
    ModerationCollection,
    ModerationRequest,
    ModerationRequestTreeNode,
)
from djangocms_moderation.utils import get_admin_url

from .utils.base import BaseViewTestCase
from .utils.factories import PlaceholderFactory, PollPluginFactory, PollVersionFactory



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
                name="cms_moderation_items_to_collection", language="en", args=()
            ),
            return_to_url="http://example.com",
            version_ids=self.pg4_version.pk,
            collection_id=self.collection1.pk,
        )
        response = self.client.post(
            path=url,
            data={"collection": self.collection1.pk, "versions": self.pg4_version.pk},
            follow=False,
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("versions", response.context["form"].errors)

    def test_add_items_to_collection_no_return_url_set(self):
        ModerationRequest.objects.all().delete()
        pg_version = PageVersionFactory(created_by=self.user)

        url = add_url_parameters(
            get_admin_url(
                name="cms_moderation_items_to_collection", language="en", args=()
            ),
            # not return url specified
            version_ids=pg_version.pk,
            collection_id=self.collection1.pk,
        )
        response = self.client.post(
            path=url,
            data={"collection": self.collection1.pk, "versions": [pg_version.pk]},
            follow=False,
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "reloadBrowser")

        self.assertTrue(
            ModerationRequest.objects.filter(
                version=pg_version, collection=self.collection1
            ).exists()
        )

    def test_add_items_to_collection_return_url_set(self):
        ModerationRequest.objects.all().delete()
        pg1_version = PageVersionFactory(created_by=self.user)
        pg2_version = PageVersionFactory(created_by=self.user)

        redirect_to_url = reverse(
            "admin:djangocms_moderation_moderationcollection_changelist"
        )

        url = add_url_parameters(
            get_admin_url(
                name="cms_moderation_items_to_collection", language="en", args=()
            ),
            return_to_url=redirect_to_url,
            version_ids=",".join(str(x) for x in [pg1_version.pk, pg2_version.pk]),
            collection_id=self.collection1.pk,
        )
        response = self.client.post(
            path=url,
            data={
                "collection": self.collection1.pk,
                "versions": [pg1_version.pk, pg2_version.pk],
            },
            follow=False,
        )

        self.assertEqual(response.status_code, 302)

        moderation_request = ModerationRequest.objects.get(version=pg1_version)
        self.assertEqual(moderation_request.collection, self.collection1)

        moderation_request = ModerationRequest.objects.get(version=pg1_version)
        self.assertEqual(moderation_request.collection, self.collection1)

        messages = list(get_messages(response.wsgi_request))
        self.assertIn(
            "2 items successfully added to moderation collection",
            [message.message for message in messages],
        )

    def test_list_versions_from_collection_id_param(self):
        ModerationRequest.objects.all().delete()

        collection1 = ModerationCollection.objects.create(
            author=self.user, name="My collection 1", workflow=self.wf1
        )
        collection2 = ModerationCollection.objects.create(
            author=self.user, name="My collection 2", workflow=self.wf1
        )

        pg1_version = PageVersionFactory(created_by=self.user)
        pg2_version = PageVersionFactory(created_by=self.user)

        collection1.add_version(pg1_version)
        collection2.add_version(pg2_version)

        new_version = PageVersionFactory(created_by=self.user)
        url = add_url_parameters(
            get_admin_url(
                name="cms_moderation_items_to_collection", language="en", args=()
            ),
            return_to_url="http://example.com",
            version_ids=new_version.pk,
            collection_id=collection1.pk,
        )

        response = self.client.get(url)
        mr1 = ModerationRequest.objects.get(version=pg1_version, collection=collection1)
        mr2 = ModerationRequest.objects.get(version=pg2_version, collection=collection2)
        # mr1 is in the list as it belongs to collection1
        self.assertIn(mr1, response.context_data["moderation_requests"])
        self.assertNotIn(mr2, response.context_data["moderation_requests"])

    def test_add_pages_moderated_children_to_collection(self):
        """
        A page with multiple moderatable children automatically adds them to the collection
        """
        collection = ModerationCollection.objects.create(
            author=self.user, name="My collection 1", workflow=self.wf1
        )
        pg_version = PageVersionFactory(created_by=self.user)
        language = pg_version.content.language

        # Populate page
        placeholder = PlaceholderFactory(source=pg_version.content)
        poll_1_version = PollVersionFactory(
            created_by=self.user, content__language=language
        )
        poll_2_version = PollVersionFactory(
            created_by=self.user, content__language=language
        )
        PollPluginFactory(placeholder=placeholder, poll=poll_1_version.content.poll)
        PollPluginFactory(placeholder=placeholder, poll=poll_2_version.content.poll)

        admin_endpoint = get_admin_url(
            name="cms_moderation_items_to_collection", language="en", args=()
        )
        url = add_url_parameters(
            admin_endpoint,
            return_to_url="http://example.com",
            version_ids=pg_version.pk,
            collection_id=collection.pk,
        )
        response = self.client.post(
            path=url,
            data={"collection": collection.pk, "versions": [pg_version.pk]},
            follow=False,
        )

        # Match collection and versions in the DB
        stored_collection = ModerationRequest.objects.filter(collection=collection)

        self.assertEqual(302, response.status_code)
        self.assertEqual(admin_endpoint, response.url)
        self.assertEqual(stored_collection.count(), 3)
        self.assertEqual(
            pg_version,
            ModerationRequest.objects.get(
                collection=collection, version=pg_version
            ).version,
        )
        self.assertEqual(
            poll_1_version,
            ModerationRequest.objects.get(
                collection=collection, version=poll_1_version
            ).version,
        )
        self.assertEqual(
            poll_2_version,
            ModerationRequest.objects.get(
                collection=collection, version=poll_2_version
            ).version,
        )

    def test_add_pages_moderated_duplicated_children_to_collection(self):
        """
        A page with multiple instances of the same version added to the collection should only
        add it to the collection once!
        """
        collection = ModerationCollection.objects.create(
            author=self.user, name="My collection 1", workflow=self.wf1
        )
        pg_version = PageVersionFactory(created_by=self.user)
        language = pg_version.content.language

        # Populate page
        placeholder = PlaceholderFactory(source=pg_version.content)
        poll_version = PollVersionFactory(
            created_by=self.user, content__language=language
        )
        PollPluginFactory(placeholder=placeholder, poll=poll_version.content.poll)
        PollPluginFactory(placeholder=placeholder, poll=poll_version.content.poll)

        admin_endpoint = get_admin_url(
            name="cms_moderation_items_to_collection", language="en", args=()
        )
        url = add_url_parameters(
            admin_endpoint,
            return_to_url="http://example.com",
            version_ids=pg_version.pk,
            collection_id=collection.pk,
        )
        response = self.client.post(
            path=url, data={"collection": collection.pk, "versions": [pg_version.pk]}
        )

        stored_collection = ModerationRequest.objects.filter(collection=collection)

        self.assertEqual(302, response.status_code)
        self.assertEqual(admin_endpoint, response.url)
        self.assertEqual(stored_collection.count(), 2)
        self.assertEqual(
            pg_version,
            ModerationRequest.objects.get(
                collection=collection, version=pg_version
            ).version,
        )
        self.assertEqual(
            poll_version,
            ModerationRequest.objects.get(
                collection=collection, version=poll_version
            ).version,
        )

    def test_add_pages_moderated_duplicated_children_to_collection_for_author_only(
        self
    ):
        """
        A page with moderatable children created by different authors only automatically adds the current users items
        """
        collection = ModerationCollection.objects.create(
            author=self.user, name="My collection 1", workflow=self.wf1
        )
        pg_version = PageVersionFactory(created_by=self.user)
        language = pg_version.content.language
        # Populate page
        placeholder = PlaceholderFactory(source=pg_version.content)
        poll_1_version = PollVersionFactory(
            created_by=self.user, content__language=language
        )
        poll_2_version = PollVersionFactory(
            created_by=self.user2, content__language=language
        )
        PollPluginFactory(placeholder=placeholder, poll=poll_1_version.content.poll)
        PollPluginFactory(placeholder=placeholder, poll=poll_2_version.content.poll)

        admin_endpoint = get_admin_url(
            name="cms_moderation_items_to_collection", language="en", args=()
        )
        url = add_url_parameters(
            admin_endpoint,
            return_to_url="http://example.com",
            version_ids=pg_version.pk,
            collection_id=collection.pk,
        )
        response = self.client.post(
            path=url, data={"collection": collection.pk, "versions": [pg_version.pk]}
        )

        stored_collection = ModerationRequest.objects.filter(collection=collection)

        self.assertEqual(302, response.status_code)
        self.assertEqual(admin_endpoint, response.url)
        self.assertEqual(stored_collection.count(), 2)

    def test_add_pages_moderated_traversed_children_to_collection(self):
        """
        A page with moderatable children that also have moderatable children: child within a child
        are added to a collection
        """
        collection = ModerationCollection.objects.create(
            author=self.user, name="My collection 1", workflow=self.wf1
        )
        pg_version = PageVersionFactory(created_by=self.user)
        language = pg_version.content.language
        # Populate page
        pg_placeholder = PlaceholderFactory(source=pg_version.content)
        poll_version = PollVersionFactory(
            created_by=self.user, content__language=language
        )
        poll_plugin = PollPluginFactory(
            placeholder=pg_placeholder, poll=poll_version.content.poll
        )
        # Populate page poll child layer 1
        poll_child_1_version = PollVersionFactory(
            created_by=self.user, content__language=language
        )
        poll_child_1_plugin = PollPluginFactory(
            placeholder=poll_plugin.placeholder, poll=poll_child_1_version.content.poll
        )
        # Populate page poll child layer 2
        poll_child_2_version = PollVersionFactory(
            created_by=self.user, content__language=language
        )
        PollPluginFactory(
            placeholder=poll_child_1_plugin.placeholder,
            poll=poll_child_2_version.content.poll,
        )

        admin_endpoint = get_admin_url(
            name="cms_moderation_items_to_collection", language="en", args=()
        )
        url = add_url_parameters(
            admin_endpoint,
            return_to_url="http://example.com",
            version_ids=pg_version.pk,
            collection_id=collection.pk,
        )
        response = self.client.post(
            path=url, data={"collection": collection.pk, "versions": [pg_version.pk]}
        )

        stored_collection = ModerationRequest.objects.filter(collection=collection)

        self.assertEqual(302, response.status_code)
        self.assertEqual(admin_endpoint, response.url)
        self.assertEqual(stored_collection.count(), 4)


class SubmitCollectionForModerationViewTest(BaseViewTestCase):
    def setUp(self):
        super(SubmitCollectionForModerationViewTest, self).setUp()
        self.url = reverse(
            "admin:cms_moderation_submit_collection_for_moderation",
            args=(self.collection2.pk,),
        )
        request_change_list_url = reverse('admin:djangocms_moderation_moderationrequest_changelist')
        self.request_change_list_url = "{}?moderation_request__collection__id={}".format(
            request_change_list_url,
            self.collection2.pk
        )

    @mock.patch.object(ModerationCollection, "submit_for_review")
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
            "admin:cms_moderation_cancel_collection", args=(self.collection2.pk,)
        )
        self.collection_change_list_url = reverse(
            "admin:djangocms_moderation_moderationcollection_changelist"
        )

    @mock.patch.object(ModerationCollection, "cancel")
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
            "admin:cms_moderation_submit_collection_for_moderation",
            args=(self.collection2.pk,),
        )
        self.url = reverse('admin:djangocms_moderation_moderationrequest_changelist')
        self.url_with_filter = "{}?moderation_request__collection__id={}".format(
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
        self.assertEqual(response.context["collection"], self.collection2)

    @mock.patch.object(ModerationCollection, "allow_submit_for_review")
    def test_change_list_view_should_contain_submit_collection_url(
        self, allow_submit_mock
    ):
        allow_submit_mock.return_value = False
        response = self.client.get(self.url_with_filter)
        self.assertNotIn("submit_for_review_url", response.context)

        allow_submit_mock.return_value = True
        response = self.client.get(self.url_with_filter)
        self.assertIn("submit_for_review_url", response.context)


class CollectionItemsViewModerationNodesTest(BaseViewTestCase):
    def setUp(self):
        """
        Node structure created

        pg_version
            layer 1
                layer 2
            layer 1
        """
        super().setUp()
        self.client.force_login(self.user)

        self.collection = ModerationCollection.objects.create(
            author=self.user, name='My collection 1', workflow=self.wf1
        )
        self.pg_version = PageVersionFactory(created_by=self.user)
        language = self.pg_version.content.language
        # Populate page
        pg_placeholder = PlaceholderFactory(source=self.pg_version.content)

        poll_version = PollVersionFactory(created_by=self.user, content__language=language)
        poll_plugin = PollPluginFactory(placeholder=pg_placeholder, poll=poll_version.content.poll)

        # Populate page poll child layer 1
        poll_child_1_version = PollVersionFactory(created_by=self.user, content__language=language)
        poll_child_1_plugin = PollPluginFactory(
            placeholder=poll_plugin.placeholder, poll=poll_child_1_version.content.poll)

        # Populate page poll child layer 2
        poll_child_2_version = PollVersionFactory(created_by=self.user, content__language=language)
        PollPluginFactory(placeholder=poll_child_1_plugin.placeholder, poll=poll_child_2_version.content.poll)

        # Same plugin in a different order
        PollPluginFactory(placeholder=pg_placeholder, poll=poll_child_1_version.content.poll)

    def test_tree_nodes_are_created(self):
        """
        Moderation request nodes are created with the correct structure
        """
        admin_endpoint = get_admin_url(
            name='cms_moderation_items_to_collection',
            language='en',
            args=()
        )
        url = add_url_parameters(
            admin_endpoint,
            return_to_url='http://example.com',
            version_ids=self.pg_version.pk,
            collection_id=self.collection.pk
        )
        response = self.client.post(
            path=url,
            data={
                'collection': self.collection.pk,
                'versions': [self.pg_version.pk],
            },
        )

        self.assertEqual(302, response.status_code)
        self.assertEqual(admin_endpoint, response.url)

        nodes = ModerationRequestTreeNode.objects.filter(moderation_request__collection_id=self.collection.pk)

        # The correct amount of nodes exist
        self.assertEqual(nodes.count(), 5)

        # The same Moderation request exists more than once in the list
        has_duplicate = False
        moderation_requests_seen = []
        for node in nodes:
            if node.moderation_request.id in moderation_requests_seen:
                has_duplicate = True
            moderation_requests_seen.append(node.moderation_request.id)
        self.assertTrue(has_duplicate)


class CollectionItemsViewModerationIntegrationTest(BaseViewTestCase):


    def test_moderation_workflow_node_deletion(self):
        """
        When a page that contains part of a tree is deleted all views work as expected

        Node structure created

        page 1
            Poll 1
                Poll 2
        Page 2
            Poll 2

        Delete page 1
        """
        self.client.force_login(self.user)

        self.collection = ModerationCollection.objects.create(
            author=self.user, name='My collection 1', workflow=self.wf1
        )
        self.page_1_version = PageVersionFactory(created_by=self.user)
        language = self.page_1_version.content.language
        # Populate page
        page_1_placeholder = PlaceholderFactory(source=self.page_1_version.content)

        # Populate page 1 poll 1 top level plugin (level 1)
        poll_version = PollVersionFactory(created_by=self.user, content__language=language)
        poll_plugin = PollPluginFactory(placeholder=page_1_placeholder, poll=poll_version.content.poll)

        # Populate page 1 poll 2 child of poll 1 (level 2)
        poll_child_1_version = PollVersionFactory(created_by=self.user, content__language=language)
        poll_child_1_plugin = PollPluginFactory(
            placeholder=poll_plugin.placeholder, poll=poll_child_1_version.content.poll)

        # Populate page 1 poll 3 child of poll 2 (level 3)
        poll_child_2_version = PollVersionFactory(created_by=self.user, content__language=language)
        PollPluginFactory(placeholder=poll_child_1_plugin.placeholder, poll=poll_child_2_version.content.poll)

        # Page 2 setup
        self.page_2_version = PageVersionFactory(created_by=self.user, content__language=language)
        page_2_placeholder = PlaceholderFactory(source=self.page_2_version.content)
        # Populate page 2 poll 3 top level plugin (level 1)
        PollPluginFactory(placeholder=page_2_placeholder, poll=poll_child_2_version.content.poll)

        # Add both pages to a collection
        admin_endpoint = get_admin_url(
            name='cms_moderation_items_to_collection',
            language='en',
            args=()
        )
        url = add_url_parameters(
            admin_endpoint,
            return_to_url='http://example.com',
            version_ids=[self.page_1_version.pk, self.page_2_version.pk],
            collection_id=self.collection.pk
        )
        response = self.client.post(
            path=url,
            data={
                'collection': self.collection.pk,
                'versions': [self.page_1_version.pk, self.page_2_version.pk],
            },
        )

        self.assertEqual(302, response.status_code)
        self.assertEqual(admin_endpoint, response.url)

        # remove page 1 from the collection
        changelist_url = reverse('admin:djangocms_moderation_moderationrequesttreenode_changelist')
        changelist_url += "?moderation_request__collection__id={}".format(self.collection.pk)

        # Choose the delete_selected action from the dropdown
        data = {
            'action': 'delete_selected',
            ACTION_CHECKBOX_NAME: [str(self.moderation_request1.pk), str(self.moderation_request2.pk)]
        }
        response = self.client.post(changelist_url, data)

        self.assertEqual(response.status_code, 200)

        # Load the page and check that the page loads and that the correct page exists
        response = self.client.get(changelist_url)
        self.assertEqual(response.status_code, 200)


