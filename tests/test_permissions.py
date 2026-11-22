from unittest.mock import patch

from django.contrib.auth.models import Permission, User
from django.urls import reverse

from cms.test_utils.testcases import CMSTestCase

from djangocms_versioning.constants import PUBLISHED
from djangocms_versioning.test_utils.factories import PageVersionFactory

from djangocms_moderation import constants
from djangocms_moderation.models import (
    CollectionComment,
    ModerationCollection,
    ModerationRequest,
    ModerationRequestTreeNode,
    RequestComment,
    Role,
    Workflow,
)


def create_staff_user(username, *codenames):
    user = User.objects.create_user(username=username, password=username, is_staff=True)
    user.user_permissions.set(Permission.objects.filter(codename__in=codenames))
    return user


class BasePermissionTestCase(CMSTestCase):
    """
    A collection in review, its author, its reviewer and an outsider: a staff
    user who holds the model permissions but takes no part in the moderation.
    """

    outsider_permissions = ()

    @classmethod
    def setUpTestData(cls):
        comment_permissions = (
            "add_collectioncomment",
            "change_collectioncomment",
            "add_requestcomment",
            "change_requestcomment",
        )
        cls.author = create_staff_user("author", *comment_permissions)
        cls.reviewer = create_staff_user("reviewer", *comment_permissions)
        cls.outsider = create_staff_user("outsider", *cls.outsider_permissions)

        cls.workflow = Workflow.objects.create(name="Workflow", is_default=True)
        role = Role.objects.create(name="Reviewer", user=cls.reviewer)
        cls.workflow.steps.create(role=role, is_required=True, order=1)

        cls.version = PageVersionFactory(created_by=cls.author)
        cls.collection = ModerationCollection.objects.create(
            author=cls.author,
            name="Private collection",
            workflow=cls.workflow,
            status=constants.IN_REVIEW,
        )
        cls.moderation_request = ModerationRequest.objects.create(
            version=cls.version,
            collection=cls.collection,
            author=cls.author,
            language="en",
        )
        cls.node = ModerationRequestTreeNode.add_root(
            moderation_request=cls.moderation_request
        )
        cls.moderation_request.actions.create(
            by_user=cls.author, action=constants.ACTION_STARTED
        )


class CollectionCommentPermissionTestCase(BasePermissionTestCase):
    outsider_permissions = ("add_collectioncomment", "change_collectioncomment")

    def setUp(self):
        self.add_url = "{}?_changelist_filters=collection__id__exact%3D{}".format(
            reverse("admin:djangocms_moderation_collectioncomment_add"),
            self.collection.pk,
        )

    def _post_data(self, **kwargs):
        data = {
            "collection": self.collection.pk,
            "message": "A comment",
            "author": self.client.session["_auth_user_id"],
        }
        data.update(kwargs)
        return data

    def test_outsider_cannot_open_add_form(self):
        self.client.force_login(self.outsider)

        response = self.client.get(self.add_url)

        self.assertEqual(response.status_code, 403)

    def test_outsider_cannot_add_comment(self):
        self.client.force_login(self.outsider)

        response = self.client.post(self.add_url, self._post_data())

        self.assertEqual(response.status_code, 403)
        self.assertFalse(CollectionComment.objects.exists())

    def test_add_view_requires_existing_collection(self):
        self.client.force_login(self.reviewer)
        url = reverse("admin:djangocms_moderation_collectioncomment_add")

        for filters in ("", "?_changelist_filters=collection__id__exact%3D0",
                        "?_changelist_filters=collection__id__exact%3Daaa"):
            with self.subTest(filters=filters):
                self.assertEqual(self.client.get(url + filters).status_code, 404)

    def test_participants_can_add_comment(self):
        for user in (self.author, self.reviewer):
            with self.subTest(user=user.username):
                self.client.force_login(user)

                self.assertEqual(self.client.get(self.add_url).status_code, 200)
                response = self.client.post(self.add_url, self._post_data())

                self.assertEqual(response.status_code, 302)
                comment = CollectionComment.objects.latest("pk")
                self.assertEqual(comment.author, user)
                self.assertEqual(comment.collection, self.collection)

    def test_posted_author_is_ignored(self):
        self.client.force_login(self.reviewer)

        response = self.client.post(
            self.add_url, self._post_data(author=self.author.pk)
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(CollectionComment.objects.get().author, self.reviewer)

    def test_posted_collection_is_ignored(self):
        other_collection = ModerationCollection.objects.create(
            author=self.outsider, name="Other collection", workflow=self.workflow
        )
        self.client.force_login(self.reviewer)

        response = self.client.post(
            self.add_url, self._post_data(collection=other_collection.pk)
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(CollectionComment.objects.get().collection, self.collection)

    def test_comment_cannot_be_moved_or_reattributed_on_change(self):
        other_collection = ModerationCollection.objects.create(
            author=self.outsider, name="Other collection", workflow=self.workflow
        )
        comment = CollectionComment.objects.create(
            collection=self.collection, author=self.reviewer, message="Original"
        )
        self.client.force_login(self.reviewer)
        url = "{}?_changelist_filters=collection__id__exact%3D{}".format(
            reverse(
                "admin:djangocms_moderation_collectioncomment_change", args=(comment.pk,)
            ),
            self.collection.pk,
        )

        response = self.client.post(
            url,
            {
                "collection": other_collection.pk,
                "message": "Edited",
                "author": self.author.pk,
            },
        )

        self.assertEqual(response.status_code, 302)
        comment.refresh_from_db()
        self.assertEqual(comment.message, "Edited")
        self.assertEqual(comment.author, self.reviewer)
        self.assertEqual(comment.collection, self.collection)

    def test_participant_cannot_change_somebody_elses_comment(self):
        comment = CollectionComment.objects.create(
            collection=self.collection, author=self.author, message="Original"
        )
        self.client.force_login(self.reviewer)
        url = "{}?_changelist_filters=collection__id__exact%3D{}".format(
            reverse(
                "admin:djangocms_moderation_collectioncomment_change", args=(comment.pk,)
            ),
            self.collection.pk,
        )

        self.assertEqual(self.client.get(url).status_code, 200)
        response = self.client.post(
            url, self._post_data(message="Edited", author=self.author.pk)
        )

        self.assertEqual(response.status_code, 403)
        comment.refresh_from_db()
        self.assertEqual(comment.message, "Original")


class RequestCommentPermissionTestCase(BasePermissionTestCase):
    outsider_permissions = ("add_requestcomment", "change_requestcomment")

    def setUp(self):
        self.add_url = "{}?_changelist_filters=moderation_request__id__exact%3D{}".format(
            reverse("admin:djangocms_moderation_requestcomment_add"),
            self.moderation_request.pk,
        )

    def _post_data(self, **kwargs):
        data = {
            "moderation_request": self.moderation_request.pk,
            "message": "A comment",
            "author": self.client.session["_auth_user_id"],
        }
        data.update(kwargs)
        return data

    def test_outsider_cannot_open_add_form(self):
        self.client.force_login(self.outsider)

        response = self.client.get(self.add_url)

        self.assertEqual(response.status_code, 403)

    def test_outsider_cannot_add_comment(self):
        self.client.force_login(self.outsider)

        response = self.client.post(self.add_url, self._post_data())

        self.assertEqual(response.status_code, 403)
        self.assertFalse(RequestComment.objects.exists())

    def test_add_view_requires_existing_moderation_request(self):
        self.client.force_login(self.reviewer)
        url = reverse("admin:djangocms_moderation_requestcomment_add")

        for filters in ("", "?_changelist_filters=moderation_request__id__exact%3D0",
                        "?_changelist_filters=moderation_request__id__exact%3Daaa"):
            with self.subTest(filters=filters):
                self.assertEqual(self.client.get(url + filters).status_code, 404)

    def test_participants_can_add_comment(self):
        for user in (self.author, self.reviewer):
            with self.subTest(user=user.username):
                self.client.force_login(user)

                self.assertEqual(self.client.get(self.add_url).status_code, 200)
                response = self.client.post(self.add_url, self._post_data())

                self.assertEqual(response.status_code, 302)
                comment = RequestComment.objects.latest("pk")
                self.assertEqual(comment.author, user)
                self.assertEqual(comment.moderation_request, self.moderation_request)

    def test_posted_author_and_moderation_request_are_ignored(self):
        other_request = ModerationRequest.objects.create(
            version=PageVersionFactory(created_by=self.outsider),
            collection=ModerationCollection.objects.create(
                author=self.outsider, name="Other collection", workflow=self.workflow
            ),
            author=self.outsider,
            language="en",
        )
        self.client.force_login(self.reviewer)

        response = self.client.post(
            self.add_url,
            self._post_data(author=self.author.pk, moderation_request=other_request.pk),
        )

        self.assertEqual(response.status_code, 302)
        comment = RequestComment.objects.get()
        self.assertEqual(comment.author, self.reviewer)
        self.assertEqual(comment.moderation_request, self.moderation_request)

    def test_participant_cannot_change_somebody_elses_comment(self):
        comment = RequestComment.objects.create(
            moderation_request=self.moderation_request,
            author=self.author,
            message="Original",
        )
        self.client.force_login(self.reviewer)
        url = "{}?_changelist_filters=moderation_request__id__exact%3D{}".format(
            reverse(
                "admin:djangocms_moderation_requestcomment_change", args=(comment.pk,)
            ),
            self.moderation_request.pk,
        )

        self.assertEqual(self.client.get(url).status_code, 200)
        response = self.client.post(
            url, self._post_data(message="Edited", author=self.author.pk)
        )

        self.assertEqual(response.status_code, 403)
        comment.refresh_from_db()
        self.assertEqual(comment.message, "Original")


class ConfirmationPagePermissionTestCase(BasePermissionTestCase):
    def _url(self, name):
        return "{}?ids={}&collection_id={}".format(
            reverse(f"admin:djangocms_moderation_moderationrequest_{name}"),
            self.node.pk,
            self.collection.pk,
        )

    def test_outsider_cannot_see_confirmation_pages(self):
        self.client.force_login(self.outsider)

        for name in ("approve", "rework", "resubmit", "publish"):
            with self.subTest(view=name):
                self.assertEqual(self.client.get(self._url(name)).status_code, 403)
                self.assertEqual(self.client.post(self._url(name)).status_code, 403)

        self.assertFalse(
            self.moderation_request.actions.exclude(
                action=constants.ACTION_STARTED
            ).exists()
        )

    def test_participants_can_see_approve_and_rework_confirmation_pages(self):
        for user in (self.author, self.reviewer):
            self.client.force_login(user)
            for name in ("approve", "rework"):
                with self.subTest(user=user.username, view=name):
                    response = self.client.get(self._url(name))

                    self.assertEqual(response.status_code, 200)
                    self.assertEqual(
                        response.context["queryset"], [self.moderation_request]
                    )

    def test_reviewer_can_still_approve(self):
        self.client.force_login(self.reviewer)

        response = self.client.post(self._url("approve"))

        self.assertEqual(response.status_code, 302)
        self.assertTrue(self.moderation_request.is_approved())


class AddItemsToCollectionPermissionTestCase(BasePermissionTestCase):
    outsider_permissions = ("add_moderationcollection",)

    def setUp(self):
        self.url = reverse("admin:cms_moderation_items_to_collection")

    def _unlocked_draft(self, user):
        version = PageVersionFactory(created_by=user)
        # Whether or not DJANGOCMS_VERSIONING_LOCK_VERSIONS is set, the
        # version lock must not be the only thing protecting a draft.
        version.locked_by = None
        version.save()
        return version

    def _add(self, user, version, collection, action=constants.COLLECTION_PUBLISH):
        self.client.force_login(user)
        return self.client.post(
            f"{self.url}?version_ids={version.pk}&action={action}",
            {"collection": collection.pk, "versions": [version.pk], "action": action},
        )

    def test_cannot_add_content_without_change_permission(self):
        version = self._unlocked_draft(self.author)
        collection = ModerationCollection.objects.create(
            author=self.outsider, name="Outsider's collection", workflow=self.workflow
        )

        response = self._add(self.outsider, version, collection)

        self.assertEqual(response.status_code, 200)
        self.assertIn("versions", response.context["form"].errors)
        self.assertFalse(collection.moderation_requests.exists())
        # The draft is still free to be worked on
        version.check_modify(self.author)

    def test_can_add_content_with_change_permission(self):
        version = self._unlocked_draft(self.author)
        editor = self.get_superuser()
        collection = ModerationCollection.objects.create(
            author=editor, name="Editor's collection", workflow=self.workflow
        )

        self._add(editor, version, collection)

        self.assertEqual(
            list(collection.moderation_requests.values_list("version", flat=True)),
            [version.pk],
        )

    @patch("djangocms_moderation.conf.ENABLE_UNPUBLISHING", True)
    def test_cannot_add_published_content_without_change_permission(self):
        version = PageVersionFactory(created_by=self.author, state=PUBLISHED)
        collection = ModerationCollection.objects.create(
            author=self.outsider,
            name="Outsider's collection",
            workflow=self.workflow,
            action=constants.COLLECTION_UNPUBLISH,
        )

        response = self._add(
            self.outsider, version, collection, action=constants.COLLECTION_UNPUBLISH
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("versions", response.context["form"].errors)
        self.assertFalse(collection.moderation_requests.exists())

    def test_contents_of_somebody_elses_collection_are_not_listed(self):
        url = f"{self.url}?collection_id={self.collection.pk}"

        for user in (self.outsider, self.reviewer):
            with self.subTest(user=user.username):
                self.client.force_login(user)

                response = self.client.get(url)

                self.assertEqual(response.status_code, 200)
                self.assertEqual(list(response.context["moderation_requests"]), [])

    def test_contents_of_own_collection_are_listed(self):
        self.client.force_login(self.author)

        response = self.client.get(f"{self.url}?collection_id={self.collection.pk}")

        self.assertEqual(
            list(response.context["moderation_requests"]), [self.moderation_request]
        )
