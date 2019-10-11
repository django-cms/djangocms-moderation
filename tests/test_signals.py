from django.urls import reverse

from cms.test_utils.testcases import CMSTestCase
from cms.test_utils.util.context_managers import signal_tester
from cms.utils.urlutils import add_url_parameters

from djangocms_moderation import constants
from djangocms_moderation.models import ModerationCollection, Role
from djangocms_moderation.signals import submitted_for_review

from .utils import factories


class SignalsTestCase(CMSTestCase):
    def test_submitted_for_review_signal(self):
        """Test that submitting for review emits a signal
        """
        moderation_request = factories.ModerationRequestFactory(
            collection__status=constants.COLLECTING
        )
        user = factories.UserFactory()
        reviewer = factories.UserFactory()

        with signal_tester(submitted_for_review) as env:
            moderation_request.collection.submit_for_review(user, reviewer)

            self.assertEqual(env.call_count, 1)

            signal = env.calls[0][1]
            self.assertEqual(signal["sender"], ModerationCollection)
            self.assertEqual(signal["collection"], moderation_request.collection)
            self.assertEqual(len(signal["moderation_requests"]), 1)
            self.assertEqual(signal["moderation_requests"][0], moderation_request)
            self.assertEqual(signal["user"], user)
            self.assertFalse(signal["rework"])

    def test_resubmitted_for_review_signal(self):
        """Test that re-submitting for review emits a signal
        """
        user = self.get_superuser()
        reviewer = factories.UserFactory()
        moderation_request = factories.ModerationRequestFactory(
            collection__status=constants.COLLECTING, author=user
        )
        moderation_request.collection.author = user
        moderation_request.collection.save()

        self.root = factories.RootModerationRequestTreeNodeFactory(
            moderation_request=moderation_request
        )
        moderation_request.collection.workflow.steps.create(
            role=Role.objects.create(name="Role 1", user=reviewer), order=1
        )
        moderation_request.update_status(
            action=constants.ACTION_REJECTED, by_user=reviewer, to_user=user
        )

        with signal_tester(submitted_for_review) as env:
            self.client.force_login(user)
            self.client.post(
                add_url_parameters(
                    reverse(
                        "admin:djangocms_moderation_moderationrequest_resubmit"
                    ),
                    collection_id=moderation_request.collection_id,
                    ids=self.root.pk,
                )
            )

            self.assertEqual(env.call_count, 1)

            signal = env.calls[0][1]
            self.assertEqual(signal["sender"], ModerationCollection)
            self.assertEqual(signal["collection"], moderation_request.collection)
            self.assertEqual(len(signal["moderation_requests"]), 1)
            self.assertEqual(signal["moderation_requests"][0], moderation_request)
            self.assertEqual(signal["user"], user)
            self.assertTrue(signal["rework"])
