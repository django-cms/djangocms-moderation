import mock

from django.contrib.admin.widgets import RelatedFieldWidgetWrapper
from django.contrib.messages import get_messages
from django.test import TransactionTestCase
from django.urls import reverse

from cms.test_utils.testcases import CMSTestCase
from cms.utils.urlutils import add_url_parameters

from djangocms_versioning.test_utils.factories import PageVersionFactory

from djangocms_moderation.models import (
    ModerationCollection,
    ModerationRequest,
    ModerationRequestTreeNode,
    Workflow,
)
from djangocms_moderation.utils import get_admin_url

from .utils.base import BaseViewTestCase
from .utils.factories import (
    ChildModerationRequestTreeNodeFactory,
    ModerationCollectionFactory,
    ModerationRequestFactory,
    PlaceholderFactory,
    PollPluginFactory,
    PollVersionFactory,
    RootModerationRequestTreeNodeFactory,
    UserFactory,
)


class CollectionItemsViewAddingRequestsTestCase(CMSTestCase):
    def test_no_eligible_items_to_add_to_collection(self):
        """
        We try add page_version to a collection but expect it to fail
        as it is already party of a collection
        """
        user = self.get_superuser()
        existing_collection = ModerationCollectionFactory(
            author=user
        )
        collection = ModerationCollectionFactory(author=user)
        page_version = PageVersionFactory(created_by=user)
        RootModerationRequestTreeNodeFactory(
            moderation_request__collection=existing_collection,
            moderation_request__version=page_version,
        )
        url = add_url_parameters(
            get_admin_url(
                name="cms_moderation_items_to_collection", language="en", args=()
            ),
            return_to_url="http://example.com",
            version_ids=page_version.pk,
            collection_id=collection.pk,
        )
        with self.login_user_context(user):
            response = self.client.post(
                path=url,
                data={"collection": collection.pk, "versions": page_version.pk},
                follow=False,
            )
        self.assertEqual(response.status_code, 200)
        self.assertIn("versions", response.context["form"].errors)
        # No new nodes were created on validation error
        self.assertEqual(ModerationRequest.objects.all().count(), 1)
        self.assertEqual(ModerationRequestTreeNode.objects.all().count(), 1)

    def test_add_items_to_collection_no_return_url_set(self):
        user = self.get_superuser()
        collection = ModerationCollectionFactory(author=user)
        page_version = PageVersionFactory(created_by=user)

        url = add_url_parameters(
            get_admin_url(
                name="cms_moderation_items_to_collection", language="en", args=()
            ),
            # no return url specified
            version_ids=page_version.pk,
            collection_id=collection.pk,
        )
        with self.login_user_context(user):
            response = self.client.post(
                path=url,
                data={"collection": collection.pk, "versions": [page_version.pk]},
                follow=False,
            )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "reloadBrowser")
        # check using success template
        self.assertListEqual(
            [t.name for t in response.templates],
            ["djangocms_moderation/request_finalized.html"],
        )

        # Moderation requests and related nodes were created
        moderation_requests = ModerationRequest.objects.filter(
            version=page_version, collection=collection
        )
        self.assertEqual(moderation_requests.count(), 1)
        self.assertEqual(
            ModerationRequestTreeNode.objects.filter(
                moderation_request=moderation_requests.get()
            ).count(),
            1,
        )

    def test_add_items_to_collection_return_url_set(self):
        user = self.get_superuser()
        collection = ModerationCollectionFactory(author=user)
        page1_version = PageVersionFactory(created_by=user)
        page2_version = PageVersionFactory(created_by=user)

        redirect_to_url = reverse(
            "admin:djangocms_moderation_moderationcollection_changelist"
        )

        url = add_url_parameters(
            get_admin_url(
                name="cms_moderation_items_to_collection", language="en", args=()
            ),
            return_to_url=redirect_to_url,
            version_ids=",".join(str(x) for x in [page1_version.pk, page2_version.pk]),
            collection_id=collection.pk,
        )
        with self.login_user_context(user):
            response = self.client.post(
                path=url,
                data={
                    "collection": collection.pk,
                    "versions": [page1_version.pk, page2_version.pk],
                },
                follow=False,
            )

        self.assertEqual(response.status_code, 302)

        moderation_request = ModerationRequest.objects.get(version=page1_version)
        self.assertEqual(moderation_request.collection, collection)
        self.assertEqual(
            ModerationRequestTreeNode.objects.filter(
                moderation_request=moderation_request
            ).count(),
            1,
        )

        moderation_request = ModerationRequest.objects.get(version=page2_version)
        self.assertEqual(moderation_request.collection, collection)
        self.assertEqual(
            ModerationRequestTreeNode.objects.filter(
                moderation_request=moderation_request
            ).count(),
            1,
        )

        messages = list(get_messages(response.wsgi_request))
        self.assertIn(
            "2 items successfully added to moderation collection",
            [message.message for message in messages],
        )

    def test_list_versions_from_collection_id_param(self):
        user = self.get_superuser()
        collection1 = ModerationCollectionFactory(author=user)
        collection2 = ModerationCollectionFactory(author=user)

        page1_version = PageVersionFactory(created_by=user)
        page2_version = PageVersionFactory(created_by=user)

        RootModerationRequestTreeNodeFactory(
            moderation_request__collection=collection1,
            moderation_request__version=page1_version,
        )
        RootModerationRequestTreeNodeFactory(
            moderation_request__collection=collection2,
            moderation_request__version=page2_version,
        )

        new_version = PageVersionFactory(created_by=user)
        url = add_url_parameters(
            get_admin_url(
                name="cms_moderation_items_to_collection", language="en", args=()
            ),
            return_to_url="http://example.com",
            version_ids=new_version.pk,
            collection_id=collection1.pk,
        )

        with self.login_user_context(user):
            response = self.client.get(url)
        mr1 = ModerationRequest.objects.get(
            version=page1_version, collection=collection1
        )
        mr2 = ModerationRequest.objects.get(
            version=page2_version, collection=collection2
        )
        # mr1 is in the list as it belongs to collection1
        self.assertIn(mr1, response.context_data["moderation_requests"])
        self.assertNotIn(mr2, response.context_data["moderation_requests"])

    def test_add_pages_moderated_children_to_collection(self):
        """
        A page with multiple moderatable children automatically adds them to the collection
        """
        user = self.get_superuser()
        collection = ModerationCollectionFactory(author=user)

        page_version = PageVersionFactory(created_by=user)
        language = page_version.content.language

        # Populate page
        placeholder = PlaceholderFactory(source=page_version.content)
        poll1_version = PollVersionFactory(created_by=user, content__language=language)
        poll2_version = PollVersionFactory(created_by=user, content__language=language)
        PollPluginFactory(placeholder=placeholder, poll=poll1_version.content.poll)
        PollPluginFactory(placeholder=placeholder, poll=poll2_version.content.poll)

        admin_endpoint = get_admin_url(
            name="cms_moderation_items_to_collection", language="en", args=()
        )
        url = add_url_parameters(
            admin_endpoint,
            return_to_url="http://example.com",
            version_ids=page_version.pk,
            collection_id=collection.pk,
        )
        with self.login_user_context(user):
            response = self.client.post(
                path=url,
                data={"collection": collection.pk, "versions": [page_version.pk]},
                follow=False,
            )

        # Match collection and versions in the DB
        stored_collection = ModerationRequest.objects.filter(collection=collection)

        self.assertEqual(302, response.status_code)
        self.assertEqual(admin_endpoint, response.url)
        self.assertEqual(stored_collection.count(), 3)
        mr = ModerationRequest.objects.filter(
            collection=collection, version=page_version
        )
        self.assertEqual(mr.count(), 1)
        self.assertEqual(
            ModerationRequestTreeNode.objects.filter(moderation_request=mr).count(), 1
        )
        mr1 = ModerationRequest.objects.filter(
            collection=collection, version=poll1_version
        )
        self.assertEqual(mr1.count(), 1)
        self.assertEqual(
            ModerationRequestTreeNode.objects.filter(moderation_request=mr1).count(), 1
        )
        mr2 = ModerationRequest.objects.filter(
            collection=collection, version=poll2_version
        )
        self.assertEqual(mr2.count(), 1)
        self.assertEqual(
            ModerationRequestTreeNode.objects.filter(moderation_request=mr2).count(), 1
        )

    def test_add_pages_moderated_duplicated_children_to_collection(self):
        """
        A page with multiple instances of the same version added to the collection should only
        add it to the collection once!
        """
        user = self.get_superuser()
        collection = ModerationCollectionFactory(author=user)

        page_version = PageVersionFactory(created_by=user)
        language = page_version.content.language

        # Populate page
        placeholder = PlaceholderFactory(source=page_version.content)
        poll_version = PollVersionFactory(created_by=user, content__language=language)
        PollPluginFactory(placeholder=placeholder, poll=poll_version.content.poll)
        PollPluginFactory(placeholder=placeholder, poll=poll_version.content.poll)

        admin_endpoint = get_admin_url(
            name="cms_moderation_items_to_collection", language="en", args=()
        )
        url = add_url_parameters(
            admin_endpoint,
            return_to_url="http://example.com",
            version_ids=page_version.pk,
            collection_id=collection.pk,
        )
        with self.login_user_context(user):
            response = self.client.post(
                path=url,
                data={"collection": collection.pk, "versions": [page_version.pk]},
            )

        stored_collection = ModerationRequest.objects.filter(collection=collection)

        self.assertEqual(302, response.status_code)
        self.assertEqual(admin_endpoint, response.url)
        self.assertEqual(stored_collection.filter(version=page_version).count(), 1)
        self.assertEqual(
            ModerationRequestTreeNode.objects.filter(
                moderation_request=stored_collection.get(version=page_version)
            ).count(),
            1,
        )
        self.assertEqual(stored_collection.filter(version=poll_version).count(), 1)
        # TODO: Check with Andrew that this should definitely have 2
        self.assertEqual(
            ModerationRequestTreeNode.objects.filter(
                moderation_request=stored_collection.get(version=poll_version)
            ).count(),
            2,
        )

    def test_add_pages_moderated_duplicated_children_to_collection_for_author_only(
        self
    ):
        """
        A page with moderatable children created by different authors only automatically adds the current users items
        """
        user = self.get_superuser()
        user2 = UserFactory()
        collection = ModerationCollectionFactory(author=user)

        page_version = PageVersionFactory(created_by=user)
        language = page_version.content.language
        # Populate page
        placeholder = PlaceholderFactory(source=page_version.content)
        poll1_version = PollVersionFactory(created_by=user, content__language=language)
        poll2_version = PollVersionFactory(created_by=user2, content__language=language)
        PollPluginFactory(placeholder=placeholder, poll=poll1_version.content.poll)
        PollPluginFactory(placeholder=placeholder, poll=poll2_version.content.poll)

        admin_endpoint = get_admin_url(
            name="cms_moderation_items_to_collection", language="en", args=()
        )
        url = add_url_parameters(
            admin_endpoint,
            return_to_url="http://example.com",
            version_ids=page_version.pk,
            collection_id=collection.pk,
        )
        with self.login_user_context(user):
            response = self.client.post(
                path=url,
                data={"collection": collection.pk, "versions": [page_version.pk]},
            )

        stored_collection = ModerationRequest.objects.filter(collection=collection)

        self.assertEqual(302, response.status_code)
        self.assertEqual(admin_endpoint, response.url)
        self.assertEqual(stored_collection.count(), 2)
        self.assertEqual(stored_collection.filter(version=page_version).count(), 1)
        self.assertEqual(
            ModerationRequestTreeNode.objects.filter(
                moderation_request=stored_collection.get(version=page_version)
            ).count(),
            1,
        )
        self.assertEqual(stored_collection.filter(version=poll1_version).count(), 1)
        self.assertEqual(
            ModerationRequestTreeNode.objects.filter(
                moderation_request=stored_collection.get(version=poll1_version)
            ).count(),
            1,
        )
        self.assertEqual(stored_collection.filter(version=poll2_version).count(), 0)
        self.assertEqual(
            ModerationRequestTreeNode.objects.filter(
                moderation_request__version=poll2_version
            ).count(),
            0,
        )

    def test_add_pages_moderated_traversed_children_to_collection(self):
        """
        A page with moderatable children that also have moderatable children: child within a child
        are added to a collection
        """
        user = self.get_superuser()
        collection = ModerationCollectionFactory(author=user)

        page_version = PageVersionFactory(created_by=user)
        language = page_version.content.language
        # Populate page
        placeholder = PlaceholderFactory(source=page_version.content)
        poll_version = PollVersionFactory(created_by=user, content__language=language)
        poll_plugin = PollPluginFactory(
            placeholder=placeholder, poll=poll_version.content.poll
        )
        # Populate page poll child layer 1
        poll_child_1_version = PollVersionFactory(
            created_by=user, content__language=language
        )
        poll_child_1_plugin = PollPluginFactory(
            placeholder=poll_plugin.placeholder, poll=poll_child_1_version.content.poll
        )
        # Populate page poll child layer 2
        poll_child_2_version = PollVersionFactory(
            created_by=user, content__language=language
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
            version_ids=page_version.pk,
            collection_id=collection.pk,
        )
        with self.login_user_context(user):
            response = self.client.post(
                path=url,
                data={"collection": collection.pk, "versions": [page_version.pk]},
            )

        stored_collection = ModerationRequest.objects.filter(collection=collection)

        self.assertEqual(302, response.status_code)
        self.assertEqual(admin_endpoint, response.url)
        self.assertEqual(stored_collection.count(), 4)
        self.assertEqual(stored_collection.filter(version=page_version).count(), 1)
        self.assertEqual(
            ModerationRequestTreeNode.objects.filter(
                moderation_request=stored_collection.get(version=page_version)
            ).count(),
            1,
        )
        self.assertEqual(stored_collection.filter(version=poll_version).count(), 1)
        self.assertEqual(
            ModerationRequestTreeNode.objects.filter(
                moderation_request=stored_collection.get(version=poll_version)
            ).count(),
            1,
        )
        self.assertEqual(
            stored_collection.filter(version=poll_child_1_version).count(), 1
        )
        self.assertEqual(
            ModerationRequestTreeNode.objects.filter(
                moderation_request=stored_collection.get(version=poll_child_1_version)
            ).count(),
            1,
        )
        self.assertEqual(
            stored_collection.filter(version=poll_child_2_version).count(), 1
        )
        self.assertEqual(
            ModerationRequestTreeNode.objects.filter(
                moderation_request=stored_collection.get(version=poll_child_2_version)
            ).count(),
            1,
        )

    def test_adding_non_page_item_doesnt_trigger_nested_collection_mechanism(self):
        user = self.get_superuser()
        collection = ModerationCollectionFactory(author=user)

        poll_version = PollVersionFactory(created_by=user)
        language = poll_version.content.language

        # Populate page
        placeholder = PlaceholderFactory(source=poll_version.content)
        poll1_version = PollVersionFactory(created_by=user, content__language=language)
        PollPluginFactory(placeholder=placeholder, poll=poll1_version.content.poll)

        admin_endpoint = get_admin_url(
            name="cms_moderation_items_to_collection", language="en", args=()
        )
        url = add_url_parameters(
            admin_endpoint,
            return_to_url="http://example.com",
            version_ids=poll_version.pk,
            collection_id=collection.pk,
        )
        with self.login_user_context(user):
            response = self.client.post(
                path=url,
                data={"collection": collection.pk, "versions": [poll_version.pk]},
            )

        stored_collection = ModerationRequest.objects.filter(collection=collection)

        self.assertEqual(302, response.status_code)
        self.assertEqual(admin_endpoint, response.url)
        self.assertEqual(stored_collection.filter(version=poll_version).count(), 1)
        self.assertEqual(
            ModerationRequestTreeNode.objects.filter(
                moderation_request=stored_collection.get(version=poll_version)
            ).count(),
            1,
        )
        self.assertEqual(stored_collection.filter(version=poll_version).count(), 1)

    def test_adding_page_not_by_the_author_doesnt_trigger_nested_collection_mechanism(
        self
    ):
        user = self.get_superuser()
        user2 = UserFactory()
        collection = ModerationCollectionFactory(author=user)

        page_version = PageVersionFactory(created_by=user2)
        language = page_version.content.language

        # Populate page
        placeholder = PlaceholderFactory(source=page_version.content)
        poll1_version = PollVersionFactory(created_by=user2, content__language=language)
        PollPluginFactory(placeholder=placeholder, poll=poll1_version.content.poll)

        admin_endpoint = get_admin_url(
            name="cms_moderation_items_to_collection", language="en", args=()
        )
        url = add_url_parameters(
            admin_endpoint,
            return_to_url="http://example.com",
            version_ids=page_version.pk,
            collection_id=collection.pk,
        )
        with self.login_user_context(user), mock.patch(
            "djangocms_moderation.forms.is_obj_version_unlocked"
        ):
            response = self.client.post(
                path=url,
                data={"collection": collection.pk, "versions": [page_version.pk]},
                follow=False,
            )

        # Match collection and versions in the DB
        stored_collection = ModerationRequest.objects.filter(collection=collection)
        self.assertEqual(302, response.status_code)
        self.assertEqual(admin_endpoint, response.url)
        self.assertEqual(stored_collection.count(), 1)
        mr = ModerationRequest.objects.filter(
            collection=collection, version=page_version
        )
        self.assertEqual(mr.count(), 1)
        self.assertEqual(
            ModerationRequestTreeNode.objects.filter(moderation_request=mr).count(), 1
        )
        mr1 = ModerationRequest.objects.filter(
            collection=collection, version=poll1_version
        )
        self.assertEqual(mr1.count(), 0)
        self.assertEqual(
            ModerationRequestTreeNode.objects.filter(moderation_request=mr1).count(), 0
        )


class CollectionItemsViewTest(CMSTestCase):
    def setUp(self):
        self.client.force_login(self.get_superuser())
        self.url = get_admin_url(
            name="cms_moderation_items_to_collection", language="en", args=()
        )

    def test_404_if_no_collection_with_specified_id(self):
        self.url += "?collection_id=15"

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 404)

    def test_404_if_collection_id_not_an_int(self):
        self.url += "?collection_id=aaa"

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 404)

    def test_moderation_requests_empty_in_context_if_no_collection_id_specified(self):
        response = self.client.get(self.url)

        self.assertListEqual(response.context["moderation_requests"], [])

    def test_initial_form_values_when_collection_id_passed(self):
        collection = ModerationCollectionFactory()
        pg_version = PageVersionFactory()
        poll_version = PollVersionFactory()
        self.url += "?collection_id=" + str(collection.pk)
        self.url += "&version_ids={},{}".format(pg_version.pk, poll_version.pk)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["form"].initial.keys()), 2)
        self.assertEqual(
            response.context["form"].initial["collection"], str(collection.pk)
        )
        self.assertQuerysetEqual(
            response.context["form"].initial["versions"],
            [pg_version.pk, poll_version.pk],
            transform=lambda o: o.pk,
            ordered=False,
        )

    def test_initial_form_values_when_collection_id_not_passed(self):
        pg_version = PageVersionFactory()
        poll_version = PollVersionFactory()
        self.url += "?version_ids={},{}".format(pg_version.pk, poll_version.pk)

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["form"].initial.keys()), 1)
        self.assertQuerysetEqual(
            response.context["form"].initial["versions"],
            [pg_version.pk, poll_version.pk],
            transform=lambda o: o.pk,
            ordered=False,
        )

    def test_initial_form_values_when_no_version_ids_passed(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["form"].initial.keys()), 1)
        self.assertEqual(response.context["form"].initial["versions"].count(), 0)

    def test_collection_widget_gets_set_on_form(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.context["form"].fields["collection"].widget.__class__,
            RelatedFieldWidgetWrapper,
        )

    def test_tree_nodes_are_created(self):
        """
        Moderation request nodes are created with the correct structure

        Created node structure:

        page_version
            layer 1
                layer 2
            layer 1
        """
        user = self.get_superuser()
        admin_endpoint = get_admin_url(
            name="cms_moderation_items_to_collection", language="en", args=()
        )
        collection = ModerationCollectionFactory(author=user)
        page_version = PageVersionFactory(created_by=user)
        placeholder = PlaceholderFactory(source=page_version.content)
        language = page_version.content.language

        poll_version = PollVersionFactory(created_by=user, content__language=language)
        poll_plugin = PollPluginFactory(
            placeholder=placeholder, poll=poll_version.content.poll
        )

        poll_child_1_version = PollVersionFactory(
            created_by=user, content__language=language
        )
        poll_child_1_plugin = PollPluginFactory(
            placeholder=poll_plugin.placeholder, poll=poll_child_1_version.content.poll
        )

        # Populate page poll child layer 2
        poll_child_2_version = PollVersionFactory(
            created_by=user, content__language=language
        )
        PollPluginFactory(
            placeholder=poll_child_1_plugin.placeholder,
            poll=poll_child_2_version.content.poll,
        )

        # Same plugin in a different order
        PollPluginFactory(
            placeholder=placeholder, poll=poll_child_1_version.content.poll
        )

        url = add_url_parameters(
            admin_endpoint,
            return_to_url="http://example.com",
            version_ids=page_version.pk,
            collection_id=collection.pk,
        )
        with self.login_user_context(user):
            response = self.client.post(
                path=url,
                data={"collection": collection.pk, "versions": [page_version.pk]},
            )

        self.assertEqual(302, response.status_code)
        self.assertEqual(admin_endpoint, response.url)

        nodes = ModerationRequestTreeNode.objects.filter(
            moderation_request__collection_id=collection.pk
        )

        # The correct amount of nodes exist
        self.assertEqual(nodes.count(), 5)
        # Tree structure is correct
        root = ModerationRequestTreeNode.get_root_nodes().get()
        self.assertEqual(root.moderation_request.version, page_version)
        self.assertEqual(root.get_children_count(), 4)
        self.assertEqual(
            root.get_children().filter(moderation_request__version=poll_version).count(), 1)
        self.assertEqual(
            root.get_children().filter(moderation_request__version=poll_child_2_version).count(), 1)
        # TODO: I thought this should be duplicated as a child and as a grandchild, not twice as the child of the same node?
        self.assertEqual(
            root.get_children().filter(moderation_request__version=poll_child_1_version).count(), 2)


class SubmitCollectionForModerationViewTest(BaseViewTestCase):
    def setUp(self):
        super(SubmitCollectionForModerationViewTest, self).setUp()
        self.url = reverse(
            "admin:cms_moderation_submit_collection_for_moderation",
            args=(self.collection2.pk,),
        )
        request_change_list_url = reverse(
            "admin:djangocms_moderation_moderationrequest_changelist"
        )
        self.request_change_list_url = "{}?moderation_request__collection__id={}".format(
            request_change_list_url, self.collection2.pk
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
        self.url = reverse("admin:djangocms_moderation_moderationrequest_changelist")
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


class TransactionCollectionItemsViewTestCase(TransactionTestCase):
    def setUp(self):
        # Create db data
        self.user = UserFactory(is_staff=True, is_superuser=True)
        self.collection = ModerationCollectionFactory(author=self.user)
        self.moderation_request1 = ModerationRequestFactory(collection=self.collection)
        self.moderation_request2 = ModerationRequestFactory(collection=self.collection)
        self.root1 = RootModerationRequestTreeNodeFactory(
            moderation_request=self.moderation_request1
        )
        self.root2 = RootModerationRequestTreeNodeFactory(
            moderation_request=self.moderation_request2
        )
        ChildModerationRequestTreeNodeFactory(
            moderation_request=self.moderation_request1, parent=self.root1
        )

        self.page_version = PageVersionFactory(created_by=self.user)

        # Login
        self.client.force_login(self.user)

        # Generate url and POST data
        self.url = add_url_parameters(
            reverse("admin:cms_moderation_items_to_collection"),
            return_to_url="http://example.com",
            version_ids=self.page_version,
            collection_id=self.collection.pk,
        )

        self.data = {"collection": self.collection.pk, "versions": self.page_version.pk}

    def tearDown(self):
        # clear content type cache for page content's versionable
        del self.moderation_request1.version.versionable.content_types

    @mock.patch("djangocms_moderation.admin.messages.success")
    def test_add_to_collection_view_is_wrapped_in_db_transaction(self, messages_mock):
        class FakeError(Exception):
            pass

        # Throw an exception to cause a db rollback.
        # Throwing FakeError as no actual code will ever throw it and
        # therefore catching this later in the test will not cover up a
        # genuine issue
        messages_mock.side_effect = FakeError

        # Do the request to add to collection view
        try:
            self.client.post(self.url, self.data)
        except FakeError:
            # This is what messages_mock should have thrown,
            # but we don't want the test to throw it.
            pass

        # Check neither the tree nodes nor the requests have been added.
        # The db transaction should have rolled back.
        self.assertEqual(ModerationRequestTreeNode.objects.all().count(), 3)
        self.assertEqual(ModerationRequest.objects.all().count(), 2)
