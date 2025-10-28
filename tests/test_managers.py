from djangocms_moderation import constants
from djangocms_moderation.models import ModerationCollection

from .utils.base import BaseTestCase


class CollectionManangerTest(BaseTestCase):

    def test_reviewers_wont_execute_too_many_queries(self):
        """This works as a stop gap that will prevent any further changes to
        execute more than 9 queries for prefetching_reviweers"""
        with self.assertNumQueries(9):
            colls = ModerationCollection.objects.all().prefetch_reviewers()
            for collection in colls:
                ModerationCollection.objects.reviewers(collection)

    def test_reviewers_returns_users_from_actions(self):
        """Test that reviewers method returns users assigned to actions"""
        # collection1 has moderation_request1 with action assigned to user2
        reviewers = ModerationCollection.objects.reviewers(self.collection1)

        self.assertIn(self.user2, reviewers)
        self.assertEqual(len(reviewers), 1)

    def test_reviewers_returns_multiple_users_from_actions(self):
        """Test that reviewers method returns all users from multiple actions"""
        # collection2 has moderation_request2 with multiple actions to user2
        reviewers = ModerationCollection.objects.reviewers(self.collection2)

        self.assertIn(self.user2, reviewers)
        self.assertEqual(len(reviewers), 1)

    def test_reviewers_returns_unique_users(self):
        """Test that reviewers method returns unique users even if assigned multiple times"""
        # Add another action with the same user to collection1
        self.moderation_request1.actions.create(
            to_user=self.user2,
            by_user=self.user,
            action=constants.ACTION_APPROVED,
            step_approved=self.wf1st1,
        )

        reviewers = ModerationCollection.objects.reviewers(self.collection1)

        # Should still be just one user (unique)
        self.assertEqual(len(reviewers), 1)
        self.assertIn(self.user2, reviewers)

    def test_reviewers_falls_back_to_first_step_role_when_no_actions_with_users(self):
        """Test that reviewers falls back to first step role users when actions have no to_user"""
        # Create a new collection with no actions or actions without to_user
        collection = ModerationCollection.objects.create(
            author=self.user,
            name="Collection No Actions",
            workflow=self.wf1,
            status=constants.IN_REVIEW  # Not COLLECTING
        )

        # Create a moderation request without actions with to_user
        from djangocms_versioning.test_utils.factories import PageVersionFactory
        version = PageVersionFactory()
        mr = collection.moderation_requests.create(
            version=version,
            language="en",
            author=self.user,
            is_active=True,
        )

        # Create action without to_user
        mr.actions.create(
            by_user=self.user,
            action=constants.ACTION_STARTED,
            to_user=None,  # No specific user assigned
        )

        reviewers = ModerationCollection.objects.reviewers(collection)

        # Should include user from first step's role (role1 -> user)
        self.assertIn(self.user, reviewers)

    def test_reviewers_does_not_fall_back_when_status_is_collecting(self):
        """Test that reviewers does not fall back to role users when status is COLLECTING"""
        # Create collection with COLLECTING status
        collection = ModerationCollection.objects.create(
            author=self.user,
            name="Collection Collecting",
            workflow=self.wf1,
            status=constants.COLLECTING
        )

        from djangocms_versioning.test_utils.factories import PageVersionFactory
        version = PageVersionFactory()
        mr = collection.moderation_requests.create(
            version=version,
            language="en",
            author=self.user,
            is_active=True,
        )

        # Create action without to_user
        mr.actions.create(
            by_user=self.user,
            action=constants.ACTION_STARTED,
            to_user=None,
        )

        reviewers = ModerationCollection.objects.reviewers(collection)

        # Should be empty since status is COLLECTING and no actions have to_user
        self.assertEqual(len(reviewers), 0)

    def test_reviewers_includes_group_users_from_first_step(self):
        """Test that reviewers includes all users from a group role in first step"""
        # Create collection with workflow that has group role as first step
        collection = ModerationCollection.objects.create(
            author=self.user,
            name="Collection Group Role",
            workflow=self.wf2,  # wf2st1 has role1 (user), wf2st2 has role3 (group)
            status=constants.IN_REVIEW
        )

        # Change first step to use group role
        self.wf2st1.delete()

        from djangocms_versioning.test_utils.factories import PageVersionFactory
        version = PageVersionFactory()
        mr = collection.moderation_requests.create(
            version=version,
            language="en",
            author=self.user,
            is_active=True,
        )

        # Create action without to_user
        mr.actions.create(
            by_user=self.user,
            action=constants.ACTION_STARTED,
            to_user=None,
        )

        reviewers = ModerationCollection.objects.reviewers(collection)

        # Should include users from group (user2 and user3)
        self.assertIn(self.user2, reviewers)
        self.assertIn(self.user3, reviewers)
        self.assertGreaterEqual(len(reviewers), 2)

    def test_reviewers_returns_empty_set_when_no_moderation_requests(self):
        """Test that reviewers returns empty set when collection has no moderation requests"""
        # Create collection without moderation requests
        collection = ModerationCollection.objects.create(
            author=self.user,
            name="Empty Collection",
            workflow=self.wf1,
        )

        reviewers = ModerationCollection.objects.reviewers(collection)

        self.assertEqual(len(reviewers), 0)
        self.assertIsInstance(reviewers, set)

    def test_reviewers_handles_workflow_without_first_step(self):
        """Test that reviewers handles workflow with no first step gracefully"""
        # Create workflow with no steps
        workflow = self.wf1
        workflow.steps.all().delete()

        collection = ModerationCollection.objects.create(
            author=self.user,
            name="Collection No Steps",
            workflow=workflow,
            status=constants.IN_REVIEW
        )

        from djangocms_versioning.test_utils.factories import PageVersionFactory
        version = PageVersionFactory()
        mr = collection.moderation_requests.create(
            version=version,
            language="en",
            author=self.user,
            is_active=True,
        )

        # Create action without to_user
        mr.actions.create(
            by_user=self.user,
            action=constants.ACTION_STARTED,
            to_user=None,
        )

        # Should not raise an error
        reviewers = ModerationCollection.objects.reviewers(collection)

        self.assertEqual(len(reviewers), 0)

    def test_reviewers_aggregates_from_multiple_moderation_requests(self):
        """Test that reviewers aggregates users from multiple moderation requests in collection"""
        # collection3 has two moderation requests with different users
        reviewers = ModerationCollection.objects.reviewers(self.collection3)

        # Both requests have actions assigned to user2
        self.assertIn(self.user2, reviewers)

        # moderation_request4 was rejected by user3
        # Note: rejected actions don't have to_user in the base setup,
        # but let's verify the behavior
        self.assertGreaterEqual(len(reviewers), 1)

    def test_reviewers_with_prefetch_is_efficient(self):
        """Test that using prefetch_reviewers makes the reviewers method efficient"""
        # This test verifies the relationship between prefetch and reviewers method
        collection = ModerationCollection.objects.prefetch_reviewers().get(pk=self.collection1.pk)

        # With prefetch, this should not trigger additional queries
        with self.assertNumQueries(0):
            reviewers = ModerationCollection.objects.reviewers(collection)

        self.assertIn(self.user2, reviewers)
