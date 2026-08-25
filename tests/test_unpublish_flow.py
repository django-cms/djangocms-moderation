from unittest import mock

from django.contrib.admin.helpers import ACTION_CHECKBOX_NAME
from django.contrib.admin.sites import AdminSite
from django.test import RequestFactory
from django.urls import reverse

from cms.models import PageContent
from cms.test_utils.testcases import CMSTestCase
from cms.test_utils.util.context_managers import signal_tester

from djangocms_versioning.constants import DRAFT, PUBLISHED, UNPUBLISHED
from djangocms_versioning.models import Version
from djangocms_versioning.test_utils.factories import PageVersionFactory

from djangocms_moderation import conf, constants
from djangocms_moderation.admin import (
    ModerationCollectionAdmin,
    ModerationRequestTreeAdmin,
)
from djangocms_moderation.admin_actions import (
    add_item_to_unpublish_collection,
    unpublish_selected,
)
from djangocms_moderation.forms import CollectionItemsForm
from djangocms_moderation.models import (
    ModerationCollection,
    ModerationRequestTreeNode,
    Role,
)
from djangocms_moderation.signals import unpublished
from djangocms_moderation.views import CollectionItemsView

from .utils import factories
from .utils.factories import PlaceholderFactory, PollPluginFactory, PollVersionFactory


class CollectionActionModelTest(CMSTestCase):
    def test_is_unpublishing_property(self):
        publish = factories.ModerationCollectionFactory(
            action=constants.COLLECTION_PUBLISH
        )
        unpublish = factories.ModerationCollectionFactory(
            action=constants.COLLECTION_UNPUBLISH
        )
        self.assertFalse(publish.is_unpublishing)
        self.assertTrue(unpublish.is_unpublishing)

    def test_action_defaults_to_publish(self):
        collection = factories.ModerationCollectionFactory()
        self.assertEqual(collection.action, constants.COLLECTION_PUBLISH)
        self.assertFalse(collection.is_unpublishing)

    def test_version_can_be_unpublished(self):
        # A published, approved request can be unpublished
        collection = factories.ModerationCollectionFactory(
            action=constants.COLLECTION_UNPUBLISH, status=constants.IN_REVIEW
        )
        author = collection.author
        role = Role.objects.create(name="Role 1", user=author)
        collection.workflow.steps.create(role=role, is_required=True, order=1)
        mr = factories.ModerationRequestFactory(
            collection=collection,
            version=PageVersionFactory(state=PUBLISHED, created_by=author),
        )
        mr.actions.create(by_user=author, action=constants.ACTION_STARTED)
        mr.update_status(constants.ACTION_APPROVED, author)

        self.assertTrue(mr.is_approved())
        self.assertTrue(mr.version_can_be_unpublished())
        # The same approved version is not a publish candidate (already published)
        self.assertFalse(mr.version_can_be_published())

    def test_approved_unpublish_request_status(self):
        collection = factories.ModerationCollectionFactory(
            action=constants.COLLECTION_UNPUBLISH, status=constants.IN_REVIEW
        )
        author = collection.author
        role = Role.objects.create(name="Role 1", user=author)
        collection.workflow.steps.create(role=role, is_required=True, order=1)
        mr = factories.ModerationRequestFactory(
            collection=collection,
            version=PageVersionFactory(state=PUBLISHED, created_by=author),
        )
        mr.actions.create(by_user=author, action=constants.ACTION_STARTED)
        mr.update_status(constants.ACTION_APPROVED, author)
        node = factories.RootModerationRequestTreeNodeFactory(moderation_request=mr)

        model_admin = ModerationRequestTreeAdmin(ModerationRequestTreeNode, AdminSite())

        self.assertEqual(model_admin.get_status(node), "Ready for unpublishing")


class UnpublishFeatureFlagTest(CMSTestCase):
    def test_flag_defaults_to_off(self):
        self.assertFalse(conf.ENABLE_UNPUBLISHING)

    def test_get_action_forces_publish_when_disabled(self):
        view = CollectionItemsView()
        view.request = self.client.request().wsgi_request
        view.request.GET = {"action": constants.COLLECTION_UNPUBLISH}
        view.request.POST = {}
        with mock.patch("djangocms_moderation.conf.ENABLE_UNPUBLISHING", False):
            self.assertEqual(view._get_action(), constants.COLLECTION_PUBLISH)

    def test_get_action_honours_unpublish_when_enabled(self):
        view = CollectionItemsView()
        view.request = self.client.request().wsgi_request
        view.request.GET = {"action": constants.COLLECTION_UNPUBLISH}
        view.request.POST = {}
        with mock.patch("djangocms_moderation.conf.ENABLE_UNPUBLISHING", True):
            self.assertEqual(view._get_action(), constants.COLLECTION_UNPUBLISH)


class CollectionItemsUnpublishFormTest(CMSTestCase):
    def setUp(self):
        self.user = factories.UserFactory(is_staff=True, is_superuser=True)
        self.publish_collection = factories.ModerationCollectionFactory(
            author=self.user,
            action=constants.COLLECTION_PUBLISH,
            status=constants.COLLECTING,
        )
        self.unpublish_collection = factories.ModerationCollectionFactory(
            author=self.user,
            action=constants.COLLECTION_UNPUBLISH,
            status=constants.COLLECTING,
        )

    def test_collection_picker_filtered_by_action(self):
        form = CollectionItemsForm(
            user=self.user, action=constants.COLLECTION_UNPUBLISH
        )
        qs = form.fields["collection"].queryset
        self.assertIn(self.unpublish_collection, qs)
        self.assertNotIn(self.publish_collection, qs)

    @mock.patch("djangocms_moderation.conf.ENABLE_UNPUBLISHING", True)
    def test_collection_widget_passes_action_to_add_popup(self):
        """
        The "+" popup would otherwise add a publish collection, which the
        picker then refuses because it is filtered by action.
        """
        request = RequestFactory().get("/")
        request.user = self.user
        form = CollectionItemsForm(
            user=self.user, action=constants.COLLECTION_UNPUBLISH
        )
        form.set_collection_widget(request)

        context = form.fields["collection"].widget.get_context(
            "collection", None, {}
        )

        self.assertIn(
            f"action={constants.COLLECTION_UNPUBLISH}", context["url_params"]
        )

    @mock.patch("djangocms_moderation.conf.ENABLE_UNPUBLISHING", False)
    def test_collection_widget_omits_action_when_unpublishing_disabled(self):
        request = RequestFactory().get("/")
        request.user = self.user
        form = CollectionItemsForm(user=self.user)
        form.set_collection_widget(request)

        context = form.fields["collection"].widget.get_context(
            "collection", None, {}
        )

        self.assertNotIn("action=", context["url_params"])

    def test_collection_error_message_names_the_required_action(self):
        published = PageVersionFactory(state=PUBLISHED, created_by=self.user)
        form = CollectionItemsForm(
            user=self.user,
            action=constants.COLLECTION_UNPUBLISH,
            data={
                # A publish collection is not in the picker's queryset
                "collection": self.publish_collection.pk,
                "versions": [published.pk],
                "action": constants.COLLECTION_UNPUBLISH,
            },
        )

        self.assertFalse(form.is_valid())
        self.assertIn("Unpublish", str(form.errors["collection"]))

    def test_published_version_eligible_for_unpublish(self):
        published = PageVersionFactory(state=PUBLISHED, created_by=self.user)
        form = CollectionItemsForm(
            user=self.user,
            action=constants.COLLECTION_UNPUBLISH,
            data={
                "collection": self.unpublish_collection.pk,
                "versions": [published.pk],
                "action": constants.COLLECTION_UNPUBLISH,
            },
        )
        self.assertTrue(form.is_valid(), form.errors)

    def test_draft_version_not_eligible_for_unpublish(self):
        draft = PageVersionFactory(state=DRAFT, created_by=self.user)
        form = CollectionItemsForm(
            user=self.user,
            action=constants.COLLECTION_UNPUBLISH,
            data={
                "collection": self.unpublish_collection.pk,
                "versions": [draft.pk],
                "action": constants.COLLECTION_UNPUBLISH,
            },
        )
        self.assertFalse(form.is_valid())

    def test_published_version_not_eligible_for_publish(self):
        published = PageVersionFactory(state=PUBLISHED, created_by=self.user)
        form = CollectionItemsForm(
            user=self.user,
            action=constants.COLLECTION_PUBLISH,
            data={
                "collection": self.publish_collection.pk,
                "versions": [published.pk],
                "action": constants.COLLECTION_PUBLISH,
            },
        )
        self.assertFalse(form.is_valid())

    def test_unpublished_version_not_eligible_for_publish(self):
        unpublished = PageVersionFactory(state=UNPUBLISHED, created_by=self.user)
        form = CollectionItemsForm(
            user=self.user,
            action=constants.COLLECTION_PUBLISH,
            data={
                "collection": self.publish_collection.pk,
                "versions": [unpublished.pk],
                "action": constants.COLLECTION_PUBLISH,
            },
        )
        self.assertFalse(form.is_valid())

    @mock.patch("djangocms_moderation.conf.ENABLE_UNPUBLISHING", True)
    def test_add_collection_popup_defaults_to_requested_action(self):
        model_admin = ModerationCollectionAdmin(ModerationCollection, AdminSite())
        request = RequestFactory().get(
            "/", {"action": constants.COLLECTION_UNPUBLISH}
        )
        request.user = self.user

        initial = model_admin.get_changeform_initial_data(request)

        self.assertEqual(initial["action"], constants.COLLECTION_UNPUBLISH)

    @mock.patch("djangocms_moderation.conf.ENABLE_UNPUBLISHING", True)
    def test_add_collection_popup_ignores_unknown_action(self):
        model_admin = ModerationCollectionAdmin(ModerationCollection, AdminSite())
        request = RequestFactory().get("/", {"action": "sideways"})
        request.user = self.user

        initial = model_admin.get_changeform_initial_data(request)

        self.assertNotIn("action", initial)

    @mock.patch("djangocms_moderation.conf.ENABLE_UNPUBLISHING", True)
    def test_collection_action_is_readonly_after_items_are_added(self):
        request = RequestFactory().get("/")
        request.user = self.user
        model_admin = ModerationCollectionAdmin(
            ModerationCollection, AdminSite()
        )
        self.assertNotIn(
            "action",
            model_admin.get_readonly_fields(request, self.unpublish_collection),
        )

        version = PageVersionFactory(state=PUBLISHED, created_by=self.user)
        self.unpublish_collection.add_version(version)

        readonly_fields = model_admin.get_readonly_fields(
            request, self.unpublish_collection
        )

        self.assertIn("action", readonly_fields)

    def test_unpublish_collection_adds_published_nested_versions(self):
        page_version = PageVersionFactory(
            state=PUBLISHED, created_by=self.user
        )
        language = page_version.content.language
        placeholder = PlaceholderFactory(source=page_version.content)
        poll_version = PollVersionFactory(
            state=PUBLISHED,
            created_by=self.user,
            content__language=language,
        )
        PollPluginFactory(
            placeholder=placeholder, poll=poll_version.content.poll
        )

        self.unpublish_collection.add_version(
            page_version, include_children=True
        )

        version_ids = set(
            self.unpublish_collection.moderation_requests.values_list(
                "version_id", flat=True
            )
        )
        self.assertEqual(version_ids, {page_version.pk, poll_version.pk})


class UnpublishAdminActionTest(CMSTestCase):
    def setUp(self):
        self.user = factories.UserFactory(is_staff=True, is_superuser=True)
        self.collection = factories.ModerationCollectionFactory(
            author=self.user,
            action=constants.COLLECTION_UNPUBLISH,
            status=constants.COLLECTING,
        )
        self.request_factory = RequestFactory()

    def test_unpublish_selected_redirects_to_finalise_view(self):
        request = self.request_factory.post(
            "/",
            data={ACTION_CHECKBOX_NAME: ["1", "2"]},
        )
        request.user = self.user
        request._collection = self.collection

        response = unpublish_selected(None, request, None)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            response.url,
            "{}?ids=1,2&collection_id={}".format(
                reverse("admin:djangocms_moderation_moderationrequest_publish"),
                self.collection.pk,
            ),
        )

    @mock.patch("djangocms_moderation.conf.ENABLE_UNPUBLISHING", False)
    def test_add_item_to_unpublish_collection_reports_disabled_feature(self):
        modeladmin = mock.Mock()
        request = self.request_factory.get("/", HTTP_REFERER="/admin/source/")

        response = add_item_to_unpublish_collection(modeladmin, request, [])

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/admin/source/")
        modeladmin.message_user.assert_called_once_with(
            request, "Unpublishing through moderation is not enabled"
        )

    @mock.patch("djangocms_moderation.conf.ENABLE_UNPUBLISHING", True)
    def test_add_item_to_unpublish_collection_redirects_with_unpublish_action(self):
        modeladmin = mock.Mock()
        version = PageVersionFactory(state=PUBLISHED, created_by=self.user)
        request = self.request_factory.get(
            "/",
            {"language": "en"},
            HTTP_REFERER="/admin/source/",
        )
        queryset = PageContent.objects.filter(pk=version.content.pk)

        response = add_item_to_unpublish_collection(modeladmin, request, queryset)

        self.assertEqual(response.status_code, 302)
        self.assertIn(f"version_ids={version.pk}", response.url)
        self.assertIn("return_to_url=%2Fadmin%2Fsource%2F", response.url)
        self.assertIn(f"action={constants.COLLECTION_UNPUBLISH}", response.url)


@mock.patch("djangocms_moderation.conf.ENABLE_UNPUBLISHING", True)
class UnpublishSelectedViewTest(CMSTestCase):
    def setUp(self):
        self.user = factories.UserFactory(is_staff=True, is_superuser=True)
        self.collection = factories.ModerationCollectionFactory(
            author=self.user,
            action=constants.COLLECTION_UNPUBLISH,
            status=constants.IN_REVIEW,
        )
        self.role1 = Role.objects.create(name="Role 1", user=self.user)
        self.role2 = Role.objects.create(
            name="Role 2",
            user=factories.UserFactory(is_staff=True, is_superuser=True),
        )
        self.collection.workflow.steps.create(role=self.role1, is_required=True, order=1)
        self.collection.workflow.steps.create(role=self.role2, is_required=True, order=2)

        self.mr = factories.ModerationRequestFactory(
            collection=self.collection,
            version=PageVersionFactory(state=PUBLISHED, created_by=self.user),
        )
        factories.RootModerationRequestTreeNodeFactory(moderation_request=self.mr)
        self.mr.actions.create(by_user=self.user, action=constants.ACTION_STARTED)
        self.mr.update_status(constants.ACTION_APPROVED, self.role1.user)
        self.mr.update_status(constants.ACTION_APPROVED, self.role2.user)

        self.client.force_login(self.user)
        self.url = reverse(
            "admin:djangocms_moderation_moderationrequesttreenode_changelist"
        )
        self.url += f"?moderation_request__collection__id={self.collection.pk}"

        self.assertTrue(self.mr.is_approved())
        self.assertEqual(self.mr.version.state, PUBLISHED)

    def _action_data(self, action):
        get_resp = self.client.get(self.url)
        return {
            "action": action,
            ACTION_CHECKBOX_NAME: [
                str(o.pk) for o in get_resp.context["cl"].queryset
            ],
        }

    @mock.patch("django.contrib.messages.success")
    def test_unpublish_selected_unpublishes_approved_request(self, messages_mock):
        data = self._action_data("unpublish_selected")
        response = self.client.post(self.url, data)
        # Follow the redirect to the finalising view
        response = self.client.post(response.url)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            messages_mock.call_args[0][1], "1 request successfully unpublished"
        )

        version = Version.objects.get(pk=self.mr.version.pk)
        self.mr.refresh_from_db()
        self.assertEqual(version.state, UNPUBLISHED)
        self.assertFalse(self.mr.is_active)

    def test_unpublished_signal_sent(self):
        data = self._action_data("unpublish_selected")
        response = self.client.post(self.url, data)
        with signal_tester(unpublished) as signal:
            self.client.post(response.url)
            self.assertEqual(signal.call_count, 1)
            _, kwargs = signal.calls[0]
            self.assertEqual(kwargs["collection"], self.collection)
            self.assertIn(self.mr, kwargs["moderation_requests"])

    def test_cannot_unpublish_while_draft_is_locked_by_another_user(self):
        editor = factories.UserFactory(is_staff=True, is_superuser=True)
        draft = self.mr.version.copy(editor)
        self.assertEqual(draft.locked_by, editor)

        data = self._action_data("unpublish_selected")
        response = self.client.post(self.url, data)
        self.client.post(response.url)

        version = Version.objects.get(pk=self.mr.version.pk)
        self.mr.refresh_from_db()
        self.assertEqual(version.state, PUBLISHED)
        self.assertTrue(self.mr.is_active)

    @mock.patch("django.contrib.messages.error")
    @mock.patch("django.contrib.messages.success")
    def test_failure_to_unpublish_is_reported_to_the_user(
        self, success_mock, error_mock
    ):
        """
        A version that passed moderation but that djangocms-versioning refuses
        to unpublish must not be reported as a success.
        """
        editor = factories.UserFactory(is_staff=True, is_superuser=True)
        self.mr.version.copy(editor)

        data = self._action_data("unpublish_selected")
        response = self.client.post(self.url, data)
        self.client.post(response.url)

        self.assertFalse(success_mock.called)
        self.assertIn("could not be unpublished", error_mock.call_args[0][1])

    def test_cannot_unpublish_request_from_another_collection(self):
        other_collection = factories.ModerationCollectionFactory(
            author=factories.UserFactory(is_staff=True, is_superuser=True),
            workflow=self.collection.workflow,
            action=constants.COLLECTION_UNPUBLISH,
            status=constants.IN_REVIEW,
        )
        other_version = PageVersionFactory(
            state=PUBLISHED, created_by=other_collection.author
        )
        other_mr = factories.ModerationRequestFactory(
            collection=other_collection, version=other_version
        )
        other_node = factories.RootModerationRequestTreeNodeFactory(
            moderation_request=other_mr
        )
        other_mr.actions.create(
            by_user=other_collection.author, action=constants.ACTION_STARTED
        )
        other_mr.update_status(constants.ACTION_APPROVED, self.role1.user)
        other_mr.update_status(constants.ACTION_APPROVED, self.role2.user)
        self.assertTrue(other_mr.version_can_be_unpublished())

        url = reverse(
            "admin:djangocms_moderation_moderationrequest_publish"
        )
        url += (
            f"?ids={other_node.pk}&collection_id={self.collection.pk}"
        )
        response = self.client.post(url)

        self.assertEqual(response.status_code, 302)
        other_version = Version.objects.get(pk=other_version.pk)
        other_mr.refresh_from_db()
        self.assertEqual(other_version.state, PUBLISHED)
        self.assertTrue(other_mr.is_active)
