from io import StringIO

from django.core.management import call_command

from cms.test_utils.testcases import CMSTestCase

from djangocms_moderation import constants
from djangocms_moderation.models import Role

from .utils import factories


class FixStatesTestCase(CMSTestCase):
    def setUp(self):
        self.user = factories.UserFactory(is_staff=True, is_superuser=True)
        self.role1 = Role.objects.create(name="Role 1", user=self.user)
        # Collection 1
        self.collection1 = factories.ModerationCollectionFactory(
            author=self.user, status=constants.IN_REVIEW)
        self.collection1.workflow.steps.create(role=self.role1, is_required=True, order=1)
        self.collection1_moderation_request1 = factories.ModerationRequestFactory(collection=self.collection1)
        factories.RootModerationRequestTreeNodeFactory(
            moderation_request=self.collection1_moderation_request1)
        self.collection1_moderation_request2 = factories.ModerationRequestFactory(collection=self.collection1)
        factories.RootModerationRequestTreeNodeFactory(
            moderation_request=self.collection1_moderation_request2)
        # Collection 2
        self.collection2 = factories.ModerationCollectionFactory(
            author=self.user, status=constants.IN_REVIEW)
        self.collection2.workflow.steps.create(role=self.role1, is_required=True, order=1)
        self.collection2_moderation_request1 = factories.ModerationRequestFactory(collection=self.collection2)
        factories.RootModerationRequestTreeNodeFactory(
            moderation_request=self.collection2_moderation_request1)
        self.collection2_moderation_request2 = factories.ModerationRequestFactory(collection=self.collection2)
        factories.RootModerationRequestTreeNodeFactory(
            moderation_request=self.collection2_moderation_request2)

        # Simulate approval of collection 1
        self.collection1_moderation_request1.actions.create(by_user=self.user, action=constants.ACTION_STARTED)
        self.collection1_moderation_request2.actions.create(by_user=self.user, action=constants.ACTION_STARTED)
        self.collection1_moderation_request1.update_status(constants.ACTION_FINISHED, self.role1.user)
        self.collection1_moderation_request2.update_status(constants.ACTION_FINISHED, self.role1.user)
        # Simulate archiving
        self.collection1.status = constants.ARCHIVED
        self.collection1.save()
        # Simulate publishing
        self.collection1_moderation_request1.version.publish(self.user)
        self.collection1_moderation_request2.version.publish(self.user)
        # Simulate approval of collection 2
        self.collection2_moderation_request1.actions.create(by_user=self.user, action=constants.ACTION_STARTED)
        self.collection2_moderation_request2.actions.create(by_user=self.user, action=constants.ACTION_STARTED)
        self.collection2_moderation_request1.update_status(constants.ACTION_FINISHED, self.role1.user)
        self.collection2_moderation_request2.update_status(constants.ACTION_FINISHED, self.role1.user)
        # Simulate archiving
        self.collection2.status = constants.ARCHIVED
        self.collection2.save()
        # Simulate publishing
        self.collection2_moderation_request1.version.publish(self.user)
        self.collection2_moderation_request2.version.publish(self.user)

        # sanity check the test setup
        self.assertEqual(self.collection1.status, constants.ARCHIVED)
        self.assertEqual(self.collection2.status, constants.ARCHIVED)

    def test_command_output_with_no_corrupted_states_dry_run(self):
        out = StringIO()
        call_command("moderation_fix_states", stdout=out)

        self.assertIn("Running Moderation Fix States command", out.getvalue())
        self.assertIn("No inconsistent ModerationRequest objects found", out.getvalue())

        out = StringIO()
        call_command("moderation_fix_states", stdout=out)

        self.assertIn("No inconsistent ModerationRequest objects found", out.getvalue())

    def test_command_output_with_no_corrupted_states(self):
        out = StringIO()
        call_command("moderation_fix_states", "--perform-fix", stdout=out)

        self.assertIn("Running Moderation Fix States command", out.getvalue())
        self.assertIn("No inconsistent ModerationRequest objects found", out.getvalue())

        out = StringIO()
        call_command("moderation_fix_states", "--perform-fix", stdout=out)

        self.assertIn("No inconsistent ModerationRequest objects found", out.getvalue())

    def test_command_output_with_corrupted_states_dry_run(self):
        out = StringIO()
        call_command("moderation_fix_states", stdout=out)

        self.assertIn("Running Moderation Fix States command", out.getvalue())
        self.assertIn("No inconsistent ModerationRequest objects found", out.getvalue())

        # Create a corrupt setup
        # Force the corruption seen in rare circumstances where is_active is left as True
        # when the version is published and the Collection is Archived
        self.collection2_moderation_request2.is_active = True
        self.collection2_moderation_request2.save()

        out = StringIO()
        call_command("moderation_fix_states", stdout=out)

        self.assertIn("ModerationRequest objects found: 1", out.getvalue())
        self.assertIn("Finished without making any changes", out.getvalue())

        # Repeating the command should show no changes have been made and the same objects are found
        out = StringIO()
        call_command("moderation_fix_states", stdout=out)

        self.assertIn("ModerationRequest objects found: 1", out.getvalue())
        self.assertIn("Finished without making any changes", out.getvalue())

    def test_command_output_with_corrupted_states(self):
        out = StringIO()
        call_command("moderation_fix_states", "--perform-fix", stdout=out)

        self.assertIn("Running Moderation Fix States command", out.getvalue())
        self.assertIn("No inconsistent ModerationRequest objects found", out.getvalue())

        # Create a corrupt setup
        # Force the corruption seen in rare circumstances where is_active is left as True
        # when the version is published and the Collection is Archived
        self.collection2_moderation_request2.is_active = True
        self.collection2_moderation_request2.save()

        out = StringIO()
        call_command("moderation_fix_states", "--perform-fix", stdout=out)

        self.assertIn("ModerationRequest objects found: 1", out.getvalue())
        self.assertIn("Repaired ModerationRequest id: %s" % self.collection2_moderation_request2.id, out.getvalue())

        # Verify fixes
        out = StringIO()
        call_command("moderation_fix_states", "--perform-fix", stdout=out)

        self.assertIn("No inconsistent ModerationRequest objects found", out.getvalue())
