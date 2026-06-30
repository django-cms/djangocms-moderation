from unittest import mock

from django.contrib.admin.helpers import ACTION_CHECKBOX_NAME
from django.urls import reverse

from cms.test_utils.testcases import CMSTestCase
from cms.test_utils.util.context_managers import signal_tester

from djangocms_versioning.constants import DRAFT, PUBLISHED, UNPUBLISHED
from djangocms_versioning.models import Version
from djangocms_versioning.test_utils.factories import PageVersionFactory

from djangocms_moderation import conf, constants
from djangocms_moderation.forms import CollectionItemsForm
from djangocms_moderation.models import Role
from djangocms_moderation.signals import unpublished
from djangocms_moderation.views import CollectionItemsView

from .utils import factories


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
