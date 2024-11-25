from unittest import mock

from django.contrib.admin.widgets import RelatedFieldWidgetWrapper
from django.contrib.messages import get_messages
from django.test import TransactionTestCase
from django.urls import reverse

from cms.test_utils.testcases import CMSTestCase
from cms.utils.urlutils import add_url_parameters, admin_reverse

from djangocms_versioning.test_utils.factories import PageVersionFactory

from djangocms_moderation.models import (
    ModerationCollection,
    ModerationRequest,
    ModerationRequestTreeNode,
)
from djangocms_moderation.utils import get_admin_url

from .utils.base import AssertQueryMixin, BaseViewTestCase
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


try:
    from djangocms_versioning.helpers import remove_version_lock, version_is_locked
except ImportError:
    from djangocms_version_locking.helpers import remove_version_lock, version_is_locked


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
        remove_version_lock(page_version)
        remove_version_lock(poll1_version)
        remove_version_lock(poll2_version)

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
            ModerationRequestTreeNode.objects.filter(moderation_request=mr.first()).count(), 1
        )
        mr1 = ModerationRequest.objects.filter(
            collection=collection, version=poll1_version
        )
        mr2 = ModerationRequest.objects.filter(
            collection=collection, version=poll2_version
        )

        self.assertEqual(mr1.count(), 1)
        self.assertEqual(
            ModerationRequestTreeNode.objects.filter(moderation_request=mr1.first()).count(), 1
        )
        self.assertEqual(mr2.count(), 1)
        self.assertEqual(
            ModerationRequestTreeNode.objects.filter(moderation_request=mr2.first()).count(), 1
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
        remove_version_lock(poll_version)

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
        mr = stored_collection.filter(version=poll_version)
        self.assertEqual(mr.count(), 1)
        self.assertEqual(
            ModerationRequestTreeNode.objects.filter(
                moderation_request=stored_collection.get(version=poll_version)
            ).count(),
            1,
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
        remove_version_lock(page_version)
        remove_version_lock(poll1_version)
        # poll2_version remains is locked, so will not be added to collection
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
        mr1 = stored_collection.filter(version=poll1_version)
        self.assertEqual(mr1.count(), 1)
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
        remove_version_lock(page_version)
        poll_version = PollVersionFactory(created_by=user, content__language=language)
        poll_plugin = PollPluginFactory(
            placeholder=placeholder, poll=poll_version.content.poll
        )
        remove_version_lock(poll_version)
        # Populate page poll child layer 1
        poll_child_1_version = PollVersionFactory(
            created_by=user, content__language=language
        )
        poll_child_1_plugin = PollPluginFactory(
            placeholder=poll_plugin.placeholder, poll=poll_child_1_version.content.poll
        )
        remove_version_lock(poll_child_1_version)
        # Populate page poll child layer 2
        poll_child_2_version = PollVersionFactory(
            created_by=user, content__language=language
        )
        PollPluginFactory(
            placeholder=poll_child_1_plugin.placeholder,
            poll=poll_child_2_version.content.poll,
        )
        remove_version_lock(poll_child_2_version)

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

        mr = stored_collection.filter(version=poll_version)
        self.assertEqual(mr.count(), 1)
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
            ModerationRequestTreeNode.objects.filter(moderation_request=mr.first()).count(), 1
        )
        mr1 = ModerationRequest.objects.filter(
            collection=collection, version=poll1_version
        )
        self.assertEqual(mr1.count(), 0)
        self.assertEqual(
            ModerationRequestTreeNode.objects.filter(moderation_request=mr1.first()).count(), 0
        )

    def test_collection_with_redirect_url_query_redirect_sanitisation(self):
        """
        Reflected XSS Protection by ensuring that harmful characters are encoded

        When a collection is successful a redirect occurs back to the grouper in versioning,
        this functionality should continue to function even when sanitised!
        """
        user = self.get_superuser()
        collection = ModerationCollectionFactory(author=user)
        page1_version = PageVersionFactory(created_by=user)
        page2_version = PageVersionFactory(created_by=user)
        opts = page1_version.versionable.version_model_proxy._meta
        redirect_to_url = admin_reverse(f"{opts.app_label}_{opts.model_name}_changelist")
        redirect_to_url += f"?page={page1_version.content.page.id}&<script>alert('attack!')</script>"

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

        messages = [message.message for message in list(get_messages(response.wsgi_request))]

        self.assertEqual(response.status_code, 302)
        self.assertIn("%3Cscript%3Ealert%28%27attack%21%27%29%3C/script%3E", response.url)
        self.assertIn(f"?page={page1_version.content.page.id}", response.url)
        self.assertIn(
            "2 items successfully added to moderation collection",
            messages,
        )
        self.assertNotIn(
            "Perhaps it was deleted",
            messages,
        )


class ModerationCollectionTestCase(CMSTestCase):
    def setUp(self):
        self.language = "en"
        self.user_1 = self.get_superuser()
        self.user_2 = UserFactory()
        self.collection = ModerationCollectionFactory(author=self.user_1)
        self.page_version = PageVersionFactory(created_by=self.user_1)
        self.placeholder = PlaceholderFactory(source=self.page_version.content)
        self.poll_version = PollVersionFactory(created_by=self.user_2, content__language=self.language)

    def test_add_version_with_locked_plugins(self):
        """
        Locked plugins should not be allowed to be added to a collection
        """
        PollPluginFactory(placeholder=self.placeholder, poll=self.poll_version.content.poll)

        admin_endpoint = get_admin_url(
            name="cms_moderation_items_to_collection", language="en", args=()
        )

        url = add_url_parameters(
            admin_endpoint,
            return_to_url="http://example.com",
            version_ids=self.page_version.pk,
            collection_id=self.collection.pk,
        )

        # Poll should be locked by default
        poll_is_locked = version_is_locked(self.poll_version)
        self.assertTrue(poll_is_locked)

        with self.login_user_context(self.user_1):
            self.client.post(
                path=url,
                data={"collection": self.collection.pk, "versions": [self.page_version.pk, self.poll_version.pk]},
                follow=False,
            )

        # Get all moderation request objects for the collection
        moderation_requests = ModerationRequest.objects.filter(collection=self.collection)

        self.assertEqual(moderation_requests.count(), 1)
        self.assertTrue(moderation_requests.filter(version=self.page_version).exists())
        self.assertFalse(moderation_requests.filter(version=self.poll_version).exists())

    def test_add_version_with_unlocked_child(self):
        """
        Only plugins that are unlocked should be added to collection
        """

        PollPluginFactory(placeholder=self.placeholder, poll=self.poll_version.content.poll)

        admin_endpoint = get_admin_url(
            name="cms_moderation_items_to_collection", language="en", args=()
        )

        url = add_url_parameters(
            admin_endpoint,
            return_to_url="http://example.com",
            version_ids=self.page_version.pk,
            collection_id=self.collection.pk,
        )

        # Poll should be locked by default
        poll_is_locked = version_is_locked(self.poll_version)
        self.assertTrue(poll_is_locked)

        # Unlock the poll version
        remove_version_lock(self.poll_version)

        with self.login_user_context(self.user_1):
            self.client.post(
                path=url,
                data={"collection": self.collection.pk, "versions": [self.page_version.pk, self.poll_version.pk]},
                follow=False,
            )

        # Get all moderation request objects for the collection
        moderation_requests = ModerationRequest.objects.filter(collection=self.collection)
        self.assertEqual(moderation_requests.count(), 2)
        self.assertTrue(moderation_requests.filter(version=self.page_version).exists())
        self.assertTrue(moderation_requests.filter(version=self.poll_version).exists())


class CollectionItemsViewTest(AssertQueryMixin, CMSTestCase):
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
        self.url += f"&version_ids={pg_version.pk},{poll_version.pk}"

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["form"].initial.keys()), 2)
        self.assertEqual(
            response.context["form"].initial["collection"], str(collection.pk)
        )
        self.assertQuerySetEqual(
            response.context["form"].initial["versions"],
            [pg_version.pk, poll_version.pk],
            transform=lambda o: o.pk,
            ordered=False,
        )

    def test_initial_form_values_when_collection_id_not_passed(self):
        pg_version = PageVersionFactory()
        poll_version = PollVersionFactory()
        self.url += f"?version_ids={pg_version.pk},{poll_version.pk}"

        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["form"].initial.keys()), 1)
        self.assertQuerySetEqual(
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

        page
            poll
                poll_child
                    poll_grandchild
            poll_child
                poll_grandchild
        """
        user = self.get_superuser()
        admin_endpoint = get_admin_url(
            name="cms_moderation_items_to_collection", language="en", args=()
        )
        collection = ModerationCollectionFactory(author=user)
        page_version = PageVersionFactory(created_by=user)
        placeholder = PlaceholderFactory(source=page_version.content)
        language = page_version.content.language

        # Populate poll
        poll_version = PollVersionFactory(created_by=user, content__language=language)
        PollPluginFactory(
            placeholder=placeholder, poll=poll_version.content.poll
        )
        remove_version_lock(poll_version)

        # Populate poll child
        poll_child_version = PollVersionFactory(
            created_by=user, content__language=language
        )
        remove_version_lock(poll_child_version)
        PollPluginFactory(
            placeholder=poll_version.content.placeholder,
            poll=poll_child_version.content.poll,
        )

        # Populate grand child
        poll_grandchild_version = PollVersionFactory(
            created_by=user, content__language=language
        )
        remove_version_lock(poll_grandchild_version)
        PollPluginFactory(
            placeholder=poll_child_version.content.placeholder,
            poll=poll_grandchild_version.content.poll,
        )

        # Add poll_child directly to page as well
        PollPluginFactory(
            placeholder=placeholder, poll=poll_child_version.content.poll
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

        # The correct number of nodes exists
        self.assertEqual(nodes.count(), 6)
        # Now assert the tree structure...
        # Check root refers to correct version & has correct number of children
        root = ModerationRequestTreeNode.get_root_nodes().get()
        self.assertEqual(root.moderation_request.version, page_version)
        self.assertEqual(root.get_children().count(), 2)
        # Check first child of root has correct tree
        poll_node = root.get_children().get(moderation_request__version=poll_version)
        self.assertEqual(poll_node.get_children().count(), 1)
        poll_child_node = poll_node.get_children().get()
        self.assertEqual(poll_child_node.moderation_request.version, poll_child_version)
        self.assertEqual(poll_child_node.get_children().count(), 1)
        poll_grandchild_node = poll_child_node.get_children().get()
        self.assertEqual(poll_grandchild_node.moderation_request.version, poll_grandchild_version)
        # Check second child of root has correct tree
        poll_child_node2 = root.get_children().get(moderation_request__version=poll_child_version)
        self.assertNotEqual(poll_child_node, poll_child_node2)
        self.assertEqual(poll_child_node2.moderation_request.version, poll_child_version)
        self.assertEqual(poll_child_node2.get_children().count(), 1)
        poll_grandchild_node2 = poll_child_node2.get_children().get()
        self.assertNotEqual(poll_grandchild_node, poll_grandchild_node2)
        self.assertEqual(poll_grandchild_node2.moderation_request.version, poll_grandchild_version)


class SubmitCollectionForModerationViewTest(BaseViewTestCase):
    def setUp(self):
        super().setUp()
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
        super().setUp()
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


class CollectionItemsViewModerationIntegrationTest(CMSTestCase):

    def setUp(self):
        self.user = self.get_superuser()
        self.client.force_login(self.user)
        self.collection = ModerationCollectionFactory(author=self.user)
        self._set_up_initial_page_data()

    def _set_up_initial_page_data(self):
        """
        This should create the following tree structure when added to collection:
            page_1_version
              poll_version
                  poll_child_version
            page_2_version
              poll_child_version
        """
        # Page 1
        self.page_1_version = PageVersionFactory(created_by=self.user)
        language = self.page_1_version.content.language
        page_1_placeholder = PlaceholderFactory(source=self.page_1_version.content)
        self.poll_version = PollVersionFactory(created_by=self.user, content__language=language)
        PollPluginFactory(placeholder=page_1_placeholder, poll=self.poll_version.content.poll)
        self.poll_child_version = PollVersionFactory(created_by=self.user, content__language=language)
        PollPluginFactory(
            placeholder=self.poll_version.content.placeholder, poll=self.poll_child_version.content.poll)
        remove_version_lock(self.page_1_version)
        remove_version_lock(self.poll_version)
        remove_version_lock(self.poll_child_version)

        # Page 2
        self.page_2_version = PageVersionFactory(created_by=self.user, content__language=language)
        page_2_placeholder = PlaceholderFactory(source=self.page_2_version.content)
        PollPluginFactory(placeholder=page_2_placeholder, poll=self.poll_child_version.content.poll)
        remove_version_lock(self.page_2_version)

    def _add_pages_to_collection(self):
        """
        As this is an integration test, adding the pages to collection
        via an http call. This ensures the tree is exactly how the add
        http call would create it.
        """
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
        # smoke check the response
        self.assertEqual(302, response.status_code)
        self.assertEqual(admin_endpoint, response.url)
        # The correct amount of moderation requests has been created
        mr = ModerationRequest.objects.filter(collection=self.collection)
        # The tree structure for page_1_version is correct
        root_1 = ModerationRequestTreeNode.get_root_nodes().get(moderation_request__version=self.page_1_version)
        self.assertEqual(mr.count(), 4)
        # The correct amount of tree nodes has been created
        # Poll is repeated twice and will therefore have an additional node
        self.assertEqual(
            ModerationRequestTreeNode.objects.filter(moderation_request__collection=self.collection).count(),
            5
        )
        self.assertEqual(root_1.get_children().count(), 1)

        child_1 = root_1.get_children().get()
        self.assertEqual(child_1.moderation_request.version, self.poll_version)
        self.assertEqual(child_1.get_children().count(), 1)
        grandchild = child_1.get_children().get()
        self.assertEqual(
            grandchild.moderation_request.version, self.poll_child_version)

        # The tree structure for page_2_version is correct
        root_2 = ModerationRequestTreeNode.get_root_nodes().get(
            moderation_request__version=self.page_2_version)
        self.assertEqual(root_2.get_children().count(), 1)
        child_2 = root_2.get_children().get()
        self.assertEqual(child_2.moderation_request.version, self.poll_child_version)
        self.assertEqual(grandchild.moderation_request, child_2.moderation_request)

    def test_moderation_workflow_node_deletion_1(self):
        """
        Add pages to a collection to create a tree structure like so:

            page_1_version
              poll_version
                  poll_child_version
            page_2_version
              poll_child_version

        Then delete page_2 version, which should make the tree like so:

            page_1_version
              poll_version

        (i.e. poll_child_version should be removed from both pages)
        """
        # Do an http call to add all the versions to collection
        # and assert the created tree is what is in the docstring
        self._add_pages_to_collection()

        # Now remove page_2_version from the collection
        page_2_root = ModerationRequestTreeNode.get_root_nodes().get(
            moderation_request__version=self.page_2_version)
        delete_url = "{}?ids={}&collection_id={}".format(
            reverse('admin:djangocms_moderation_moderationrequesttreenode_delete'),
            ",".join([str(page_2_root.pk)]),
            self.collection.pk,
        )
        response = self.client.post(delete_url, follow=True)
        self.assertEqual(response.status_code, 200)

        # Load the changelist and check that the page loads without an error
        changelist_url = reverse('admin:djangocms_moderation_moderationrequesttreenode_changelist')
        changelist_url += f"?moderation_request__collection__id={self.collection.pk}"
        response = self.client.get(changelist_url)
        self.assertEqual(response.status_code, 200)

        # Check the data
        # The whole of the page_2_version tree should have been removed.
        # Additionally, poll_child_version should have been removed from
        # the page_1_version tree.
        self.assertEqual(
            ModerationRequest.objects.filter(collection=self.collection).count(),
            2
        )
        self.assertEqual(
            ModerationRequestTreeNode.objects.filter(moderation_request__collection=self.collection).count(),
            2
        )
        self.assertEqual(ModerationRequestTreeNode.get_root_nodes().count(), 1)
        root = ModerationRequestTreeNode.get_root_nodes().get()
        self.assertEqual(root.moderation_request.version, self.page_1_version)
        self.assertEqual(root.get_children().count(), 1)
        self.assertEqual(root.get_children().get().moderation_request.version, self.poll_version)

    def test_moderation_workflow_node_deletion_2(self):
        """
        Add pages to a collection to create a tree structure like so:

            page_1_version
              poll_version
                  poll_child_version
            page_2_version
              poll_child_version

        Then delete page_1_version, which should make the tree like so:

            page_2_version

        (i.e. poll_child_version should be removed from both pages)
        """
        # Do an http call to add all the versions to collection
        # and assert the created tree is what is in the docstring
        self._add_pages_to_collection()

        # Now remove page_1_version from the collection
        page_1_root = ModerationRequestTreeNode.get_root_nodes().get(
            moderation_request__version=self.page_1_version)
        delete_url = "{}?ids={}&collection_id={}".format(
            reverse('admin:djangocms_moderation_moderationrequesttreenode_delete'),
            ",".join([str(page_1_root.pk)]),
            self.collection.pk,
        )
        response = self.client.post(delete_url, follow=True)
        self.assertEqual(response.status_code, 200)

        # Load the changelist and check that the page loads without an error
        changelist_url = reverse('admin:djangocms_moderation_moderationrequesttreenode_changelist')
        changelist_url += f"?moderation_request__collection__id={self.collection.pk}"
        response = self.client.get(changelist_url)
        self.assertEqual(response.status_code, 200)

        # Check the data
        # The whole of the page_1_version tree should have been removed.
        # Additionally, poll_child_version should have been removed from
        # the page_2_version tree.
        self.assertEqual(
            ModerationRequest.objects.filter(collection=self.collection).count(),
            1
        )
        self.assertEqual(
            ModerationRequestTreeNode.objects.filter(moderation_request__collection=self.collection).count(),
            1
        )
        self.assertEqual(ModerationRequestTreeNode.get_root_nodes().count(), 1)
        root = ModerationRequestTreeNode.get_root_nodes().get()
        self.assertEqual(root.moderation_request.version, self.page_2_version)
        self.assertEqual(root.get_children().count(), 0)

    def test_moderation_workflow_node_deletion_3(self):
        """
        Add pages to a collection to create a tree structure like so:

            page_1_version
              poll_version
                  poll_child_version
            page_2_version
              poll_child_version

        Then delete poll_version, which should make the tree like so:

            page_1_version
            page_2_version

        (i.e. poll_child_version should be removed from both pages)
        """
        # Do an http call to add all the versions to collection
        # and assert the created tree is what is in the docstring
        self._add_pages_to_collection()

        # Now remove poll_version from the collection
        page_1_root = ModerationRequestTreeNode.get_root_nodes().get(
            moderation_request__version=self.page_1_version)
        page_1_root_children = page_1_root.get_children()
        if page_1_root_children.count() > 0:
            poll_1_node = page_1_root_children.get()
            delete_url = "{}?ids={}&collection_id={}".format(
                reverse('admin:djangocms_moderation_moderationrequesttreenode_delete'),
                ",".join([str(poll_1_node.pk)]),
                self.collection.pk,
            )
            response = self.client.post(delete_url, follow=True)
            self.assertEqual(response.status_code, 200)

        # Load the changelist and check that the page loads without an error
        changelist_url = reverse('admin:djangocms_moderation_moderationrequesttreenode_changelist')
        changelist_url += f"?moderation_request__collection__id={self.collection.pk}"
        response = self.client.get(changelist_url)
        self.assertEqual(response.status_code, 200)

        # Check the data
        # Only the roots (page_1_version and page_2_version) should remain
        self.assertEqual(
            ModerationRequest.objects.filter(collection=self.collection).count(),
            2
        )
        self.assertEqual(
            ModerationRequestTreeNode.objects.filter(moderation_request__collection=self.collection).count(),
            2
        )
        self.assertEqual(ModerationRequestTreeNode.get_root_nodes().count(), 2)
        self.assertEqual(
            ModerationRequestTreeNode.objects.filter(moderation_request__version=self.page_1_version).count(),
            1
        )
        self.assertEqual(
            ModerationRequestTreeNode.objects.filter(moderation_request__version=self.page_2_version).count(),
            1
        )

    def test_moderation_workflow_node_deletion_4(self):
        """
        Add pages to a collection to create a tree structure like so:

            page_1_version
              poll_version
                  poll_child_version
            page_2_version
              poll_child_version

        Then delete poll_child_version from the page 1 tree, which should make the tree like so:

            page_1_version
              poll_version
            page_2_version

        (i.e. poll_child_version should be removed from both pages)
        """
        # Do an http call to add all the versions to collection
        # and assert the created tree is what is in the docstring
        self._add_pages_to_collection()

        # Now remove poll_version from the collection
        page_1_root = ModerationRequestTreeNode.get_root_nodes().get(
            moderation_request__version=self.page_1_version)
        page_1_root_children = page_1_root.get_children()
        if page_1_root_children.count() > 0:
            poll_grandchild_node = page_1_root_children.get().get_children().get()
            delete_url = "{}?ids={}&collection_id={}".format(
                reverse('admin:djangocms_moderation_moderationrequesttreenode_delete'),
                ",".join([str(poll_grandchild_node.pk)]),
                self.collection.pk,
            )
            response = self.client.post(delete_url, follow=True)
            self.assertEqual(response.status_code, 200)

        # Load the changelist and check that the page loads without an error
        changelist_url = reverse('admin:djangocms_moderation_moderationrequesttreenode_changelist')
        changelist_url += f"?moderation_request__collection__id={self.collection.pk}"
        response = self.client.get(changelist_url)
        self.assertEqual(response.status_code, 200)

        # Check the data
        # Only the roots (page_1_version and page_2_version) should remain
        self.assertEqual(
            ModerationRequest.objects.filter(collection=self.collection).count(),
            3
        )
        self.assertEqual(
            ModerationRequestTreeNode.objects.filter(moderation_request__collection=self.collection).count(),
            3
        )
        self.assertEqual(ModerationRequestTreeNode.get_root_nodes().count(), 2)
        root_1 = ModerationRequestTreeNode.get_root_nodes().filter(
            moderation_request__version=self.page_1_version).get()
        root_2 = ModerationRequestTreeNode.get_root_nodes().filter(
            moderation_request__version=self.page_2_version).get()
        self.assertEqual(root_1.get_children().count(), 1)
        self.assertEqual(root_2.get_children().count(), 0)

    def test_moderation_workflow_node_deletion_5(self):
        """
        Add pages to a collection to create a tree structure like so:

            page_1_version
              poll_version
                  poll_child_version
            page_2_version
              poll_child_version

        Then delete poll_child_version from the page 2 tree, which should make the tree like so:

            page_1_version
              poll_version
            page_2_version

        (i.e. poll_child_version should be removed from both pages)
        """
        # Do an http call to add all the versions to collection
        # and assert the created tree is what is in the docstring
        self._add_pages_to_collection()

        # Now remove poll_version from the collection
        page_2_root = ModerationRequestTreeNode.get_root_nodes().get(
            moderation_request__version=self.page_2_version)
        page_2_root_children = page_2_root.get_children()
        if page_2_root_children.count() > 0:
            poll_child_node = page_2_root_children.get()
            delete_url = "{}?ids={}&collection_id={}".format(
                reverse('admin:djangocms_moderation_moderationrequesttreenode_delete'),
                ",".join([str(poll_child_node.pk)]),
                self.collection.pk,
            )
            response = self.client.post(delete_url, follow=True)
            self.assertEqual(response.status_code, 200)

        # Load the changelist and check that the page loads without an error
        changelist_url = reverse('admin:djangocms_moderation_moderationrequesttreenode_changelist')
        changelist_url += f"?moderation_request__collection__id={self.collection.pk}"
        response = self.client.get(changelist_url)
        self.assertEqual(response.status_code, 200)

        # Check the data
        # Only the roots (page_1_version and page_2_version) should remain
        self.assertEqual(
            ModerationRequest.objects.filter(collection=self.collection).count(),
            3
        )
        self.assertEqual(
            ModerationRequestTreeNode.objects.filter(moderation_request__collection=self.collection).count(),
            3
        )
        self.assertEqual(ModerationRequestTreeNode.get_root_nodes().count(), 2)
        root_1 = ModerationRequestTreeNode.get_root_nodes().filter(
            moderation_request__version=self.page_1_version).get()
        root_2 = ModerationRequestTreeNode.get_root_nodes().filter(
            moderation_request__version=self.page_2_version).get()

        self.assertEqual(root_1.get_children().count(), 1)
        self.assertEqual(root_1.get_children().get().moderation_request.version, self.poll_version)
        self.assertEqual(root_2.get_children().count(), 0)
