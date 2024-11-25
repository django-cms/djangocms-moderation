import json
from unittest import mock, skip

from django.template.defaultfilters import truncatechars
from django.urls import reverse

from cms.test_utils.testcases import CMSTestCase

from djangocms_versioning.test_utils.factories import PageVersionFactory

from djangocms_moderation.conf import COLLECTION_NAME_LENGTH_LIMIT
from djangocms_moderation.constants import COLLECTING, IN_REVIEW
from djangocms_moderation.helpers import (
    get_form_submission_for_step,
    get_moderated_children_from_placeholder,
    get_moderation_button_title_and_url,
    get_page_or_404,
    is_obj_version_unlocked,
)
from djangocms_moderation.models import (
    ConfirmationFormSubmission,
    ConfirmationPage,
    ModerationCollection,
    ModerationRequest,
)

from .utils.base import BaseTestCase
from .utils.factories import (
    NoneModeratedPollPluginFactory,
    NoneModeratedPollVersionFactory,
    PlaceholderFactory,
    PollPluginFactory,
    PollVersionFactory,
)
from .utils.moderated_polls.factories import (
    DeeplyNestedPollPluginFactory,
    ManytoManyPollPluginFactory,
    NestedPollPluginFactory,
)


@skip("Confirmation page feature doesn't support 1.0.x yet")
class GetPageOr404Test(BaseTestCase):
    def test_returns_page(self):
        self.assertEqual(get_page_or_404(self.pg1_version.pk, "en"), self.pg1_version)


class GetFormSubmissions(BaseTestCase):
    def test_returns_form_submission_for_step(self):
        cp = ConfirmationPage.objects.create(name="Checklist Form")
        self.role1.confirmation_page = cp
        self.role1.save()

        cfs1 = ConfirmationFormSubmission.objects.create(
            moderation_request=self.moderation_request1,
            for_step=self.wf1st1,
            by_user=self.user,
            data=json.dumps([{"label": "Question 1", "answer": "Yes"}]),
            confirmation_page=cp,
        )
        ConfirmationFormSubmission.objects.create(
            moderation_request=self.moderation_request1,
            for_step=self.wf1st2,
            by_user=self.user,
            data=json.dumps([{"label": "Question 1", "answer": "Yes"}]),
            confirmation_page=cp,
        )
        result = get_form_submission_for_step(
            active_request=self.moderation_request1, current_step=self.wf1st1
        )
        self.assertEqual(result, cfs1)


class VersionLockingTestCase(BaseTestCase):
    def test_is_obj_version_unlocked(self):
        version = PageVersionFactory(created_by=self.user)
        self.assertTrue(is_obj_version_unlocked(version.content, self.user))
        self.assertFalse(is_obj_version_unlocked(version.content, self.user2))

        # Make sure that we are actually calling the version-lock method and it
        # still exists
        with mock.patch(
            "djangocms_moderation.helpers.content_is_unlocked_for_user",
            return_value=True,
        ) as _mock:
            self.assertTrue(is_obj_version_unlocked(version.content, self.user2))
            _mock.assert_called_once_with(version.content, self.user2)

    def test_is_obj_version_unlocked_when_locking_is_not_installed(self):
        with mock.patch(
            "djangocms_moderation.helpers.content_is_unlocked_for_user"
        ) as _mock:
            _mock = None  # noqa
            version = PageVersionFactory(created_by=self.user)
            self.assertTrue(is_obj_version_unlocked(version.content, self.user3))


class ModerationButtonLinkAndUrlTestCase(BaseTestCase):
    def setUp(self):
        self.collection = ModerationCollection.objects.create(
            author=self.user, name="C1", workflow=self.wf1, status=COLLECTING
        )
        version = PageVersionFactory(created_by=self.user)

        self.collection.add_version(version)

        self.mr = ModerationRequest.objects.get(
            version=version, collection=self.collection
        )
        self.expected_url = "{}?moderation_request__collection__id={}".format(
            reverse('admin:djangocms_moderation_moderationrequest_changelist'),
            self.collection.id,
        )

    def test_get_moderation_button_title_and_url_when_collection(self):
        title, url = get_moderation_button_title_and_url(self.mr)
        self.assertEqual(title, f'In collection "C1 ({self.collection.id})"')
        self.assertEqual(url, self.expected_url)

    def test_get_moderation_button_title_and_url_when_in_review(self):
        self.collection.status = IN_REVIEW
        self.collection.save()

        title, url = get_moderation_button_title_and_url(self.mr)
        self.assertEqual(title, f'In moderation "C1 ({self.collection.id})"')
        self.assertEqual(url, self.expected_url)

    def test_get_moderation_button_truncated_title_and_url(self):
        self.collection.name = "Very long collection name so long wow!"
        self.collection.save()
        title, url = get_moderation_button_title_and_url(self.mr)

        expected_title = truncatechars(self.collection.name, COLLECTION_NAME_LENGTH_LIMIT)
        self.assertEqual(
            title,
            # By default, truncate will shorten the name
            f'In collection "{expected_title} ({self.collection.id})"',
        )
        with mock.patch("djangocms_moderation.helpers.COLLECTION_NAME_LENGTH_LIMIT", 3):
            title, url = get_moderation_button_title_and_url(self.mr)
            expected_title = truncatechars(self.collection.name, 3)
            self.assertEqual(
                title,
                # As the limit is only 3, the truncate will produce `...`
                f'In collection "{expected_title} ({self.collection.id})"',
            )

        with mock.patch(
            "djangocms_moderation.helpers.COLLECTION_NAME_LENGTH_LIMIT", None
        ):
            # None means no limit
            title, url = get_moderation_button_title_and_url(self.mr)
            self.assertEqual(
                title,
                'In collection "Very long collection name so long wow! ({})"'.format(
                    self.collection.id
                ),
            )

        self.assertEqual(url, self.expected_url)


class ModeratedChildrenTestCase(CMSTestCase):
    def setUp(self):
        self.user = self.get_superuser()

    def test_get_moderated_children_from_placeholder_has_only_registered_model(self):
        """
        The moderated model is the only model registered with moderation
        """
        pg_version = PageVersionFactory(created_by=self.user)
        language = pg_version.content.language

        # Populate page
        placeholder = PlaceholderFactory(source=pg_version.content)
        # Moderated plugin
        poll_version = PollVersionFactory(
            created_by=self.user, content__language=language
        )
        PollPluginFactory(placeholder=placeholder, poll=poll_version.content.poll)
        # None moderated plugin
        none_moderated_poll_version = NoneModeratedPollVersionFactory(
            created_by=self.user, content__language=language
        )
        NoneModeratedPollPluginFactory(
            placeholder=placeholder, poll=none_moderated_poll_version.content.poll
        )

        moderated_children = list(
            get_moderated_children_from_placeholder(
                placeholder, {"language": pg_version.content.language}
            )
        )

        self.assertEqual(moderated_children, [poll_version])

    def test_get_moderated_children_from_placeholder_gets_correct_versions(self):
        """
        Models from a page with two different languages are filtered correctly
        """
        language_1 = "en"
        language_2 = "fr"
        # Populate page 1
        pg_1_version = PageVersionFactory(
            created_by=self.user, content__language=language_1
        )
        pg_1_placeholder = PlaceholderFactory(source=pg_1_version.content)
        pg_1_poll_version = PollVersionFactory(
            created_by=self.user, content__language=language_1
        )
        PollPluginFactory(
            placeholder=pg_1_placeholder, poll=pg_1_poll_version.content.poll
        )
        # Populate page 2
        pg_2_version = PageVersionFactory(
            created_by=self.user,
            content__language=language_2,
            content__page=pg_1_version.grouper,
        )
        pg_2_placeholder = PlaceholderFactory(source=pg_2_version.content)
        pg_2_poll_version = PollVersionFactory(
            created_by=self.user, content__language=language_2
        )
        PollPluginFactory(
            placeholder=pg_2_placeholder, poll=pg_2_poll_version.content.poll
        )

        page_1_moderated_children = list(
            get_moderated_children_from_placeholder(
                pg_1_placeholder, {"language": pg_1_version.content.language}
            )
        )
        page_2_moderated_children = list(
            get_moderated_children_from_placeholder(
                pg_2_placeholder, {"language": pg_2_version.content.language}
            )
        )

        self.assertEqual(page_1_moderated_children, [pg_1_poll_version])
        self.assertEqual(page_2_moderated_children, [pg_2_poll_version])

    def test_get_moderated_children_from_placeholder_gets_nested_models(self):
        """
        Versionable models that are nested inside a custom plugin model
        can be found when adding to a collection.
        """
        pg_version = PageVersionFactory(created_by=self.user)
        language = pg_version.content.language

        # Populate page
        placeholder = PlaceholderFactory(source=pg_version.content)
        # Moderated plugin
        poll_version = PollVersionFactory(
            created_by=self.user, content__language=language
        )
        # Nested versioned poll
        NestedPollPluginFactory(placeholder=placeholder, nested_poll__poll=poll_version.content.poll)

        moderated_children = list(
            get_moderated_children_from_placeholder(
                placeholder, {"language": pg_version.content.language}
            )
        )

        self.assertEqual(moderated_children, [poll_version])

    def test_get_moderated_children_from_placeholder_gets_plugin_with_m2m_fields(self):
        """
        FIXME: Currently only checks that a M2M nested poll entry does not cause an error.
        """
        pg_version = PageVersionFactory(created_by=self.user)
        language = pg_version.content.language
        placeholder = PlaceholderFactory(source=pg_version.content)
        poll_1_version = PollVersionFactory(
            created_by=self.user, content__language=language
        )
        poll_2_version = PollVersionFactory(
            created_by=self.user, content__language=language
        )
        ManytoManyPollPluginFactory(placeholder=placeholder, polls=[
            poll_1_version.content.poll,
            poll_2_version.content.poll,
        ])

        moderated_children = list(
            get_moderated_children_from_placeholder(
                placeholder, {"language": pg_version.content.language}
            )
        )

        # FIXME:
        #       This test is only covering that the M2M field doesn't cause an error.
        #       It should see that the nested polls are found
        #       self.assertEqual(moderated_children, [poll_1_version, poll_2_version])
        self.assertEqual(moderated_children, [])

    def test_get_moderated_children_from_placeholder_gets_deeply_nested_models(self):
        """
        Versionable models that are deeply nested inside a custom plugin model
        can be found when adding to a collection.
        """
        pg_version = PageVersionFactory(created_by=self.user)
        language = pg_version.content.language

        # Populate page
        placeholder = PlaceholderFactory(source=pg_version.content)
        # Moderated plugin
        poll_version = PollVersionFactory(
            created_by=self.user, content__language=language
        )
        # Deeply nested versioned poll
        DeeplyNestedPollPluginFactory(
            placeholder=placeholder,
            deeply_nested_poll__nested_poll__poll=poll_version.content.poll
        )

        moderated_children = list(
            get_moderated_children_from_placeholder(
                placeholder, {"language": pg_version.content.language}
            )
        )

        self.assertEqual(moderated_children, [poll_version])
