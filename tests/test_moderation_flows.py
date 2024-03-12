from unittest import skip

from django.contrib.auth.models import User
from django.test import TestCase

from cms.api import create_page
from cms.utils.urlutils import admin_reverse

from djangocms_moderation import constants
from djangocms_moderation.models import (
    ModerationRequest,
    ModerationRequestAction,
    Role,
    Workflow,
)
from djangocms_moderation.utils import get_admin_url


@skip("1.0.x rework TBC")
class ModerationFlowsTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.workflow = Workflow.objects.create(
            name="Workflow 1", is_default=True, requires_compliance_number=True
        )

        # create users, groups and roles
        cls.author = User.objects.create_superuser(
            username="test1", email="test1@test1.com", password="test1"
        )
        cls.moderator_1 = User.objects.create_superuser(
            username="test2", email="test2@test.com", password="test2"
        )
        cls.moderator_2 = User.objects.create_superuser(
            username="test3", email="test3@test.com", password="test3"
        )

        cls.page = create_page(
            title="Page 1", template="page.html", language="en", created_by=cls.author
        )

        cls.role1 = Role.objects.create(name="Role 1", user=cls.moderator_1)
        cls.role2 = Role.objects.create(name="Role 2", user=cls.moderator_2)

        cls.page = create_page(
            title="Page 1", template="page.html", language="en", created_by=cls.author
        )

        cls.step1 = cls.workflow.steps.create(role=cls.role1, is_required=True, order=1)
        cls.step2 = cls.workflow.steps.create(role=cls.role2, is_required=True, order=2)

    def _process_moderation_request(self, user, action, message="Test message"):
        self.client.force_login(user)
        response = self.client.post(
            get_admin_url(
                name=f"cms_moderation_{action}_request",
                language="en",
                args=(self.page.pk, "en"),
            ),
            data={"message": message},
        )
        return response

    def _approve_moderation_request(self, user, message="Test message - approved"):
        return self._process_moderation_request(user, "approve", message)

    def _reject_moderation_request(self, user, message="Test message - rejected"):
        return self._process_moderation_request(user, "reject", message)

    def _new_moderation_request(self, user, message="Test message - new"):
        return self._process_moderation_request(user, "new", message)

    def _resubmit_moderation_request(self, user, message="Test message - resubmit"):
        return self._process_moderation_request(user, "resubmit", message)

    def _cancel_moderation_request(self, user, message="Test message - cancel"):
        return self._process_moderation_request(user, "cancel", message)

    def test_approve_moderation_workflow(self):
        """
        This case tests the following workflow:
        1. author creates a new moderation request
        2. moderator_1 approves the first stage
        3. moderator_1 tries to approve the second stage - it should not work
        4. moderator_2 approves
        5. compliance number is generated
        6. author publishes the page and workflow is done
        """
        self.assertFalse(ModerationRequest.objects.exists())
        self.assertFalse(ModerationRequestAction.objects.exists())

        # Lets create a new moderation request
        self._new_moderation_request(self.author)

        moderation_request = ModerationRequest.objects.get()  # It exists
        action = ModerationRequestAction.objects.get()
        self.assertEqual(action.action, constants.ACTION_STARTED)

        response = self._approve_moderation_request(self.moderator_1)
        self.assertEqual(response.status_code, 200)

        second_action = ModerationRequestAction.objects.last()
        self.assertTrue(second_action.action, constants.ACTION_APPROVED)
        self.assertTrue(second_action.message, "Test message - approved")
        # Compliance number is not generated yet
        self.assertIsNone(moderation_request.compliance_number)

        # moderator_1 can't approve the second request, so they will get 403
        response = self._approve_moderation_request(self.moderator_1)
        self.assertEqual(response.status_code, 403)

        # moderator_2 can approve, as per workflow setup
        response = self._approve_moderation_request(self.moderator_2, "message #2")
        self.assertEqual(response.status_code, 200)

        moderation_request.refresh_from_db()
        self.assertEqual(moderation_request.author, self.author)
        self.assertTrue(moderation_request.is_active)
        compliance_number = moderation_request.compliance_number
        self.assertIsNotNone(compliance_number)

        third_action = ModerationRequestAction.objects.last()
        self.assertTrue(third_action.action, constants.ACTION_APPROVED)
        self.assertTrue(second_action.message, "message #2")

        # Now the original author can publish the changes
        self.client.force_login(self.author)
        self.client.post(
            admin_reverse("cms_page_publish_page", args=(self.page.pk, "en"))
        )
        moderation_request.refresh_from_db()
        # Moderation request is finished and last action is recorded
        self.assertFalse(moderation_request.is_active)
        last_action = ModerationRequestAction.objects.last()
        self.assertTrue(last_action.action, constants.ACTION_FINISHED)
        self.assertEqual(moderation_request.compliance_number, compliance_number)

    def test_reject_moderation_workflow(self):
        """
        This case tests the following workflow:
        1. author creates a new moderation request
        2. moderator_1 approves the first stage
        3. moderator_2 rejects the changes
        4. author resubmits the amends
        5. all is approved by moderator_1 and moderator_2
        6. author cancels the request
        """
        self.assertFalse(ModerationRequest.objects.exists())
        self.assertFalse(ModerationRequestAction.objects.exists())

        # Lets create a new moderation request
        self._new_moderation_request(self.author)

        moderation_request = ModerationRequest.objects.get()  # It exists

        action = ModerationRequestAction.objects.get()
        self.assertEqual(action.action, constants.ACTION_STARTED)

        # moderator_1 will approve it now
        response = self._approve_moderation_request(self.moderator_1)
        self.assertEqual(response.status_code, 200)

        # moderator_2 rejects the changes
        response = self._reject_moderation_request(
            self.moderator_2, "Please, less swearing"
        )
        self.assertEqual(response.status_code, 200)

        moderation_request.refresh_from_db()
        # Make sure that after the rejection, this moderation request is still active
        self.assertTrue(moderation_request.is_active)

        third_action = ModerationRequestAction.objects.last()
        self.assertTrue(third_action.action, constants.ACTION_REJECTED)
        self.assertTrue(third_action.message, "Please, less swearing")

        # Lets check that we now have 2 archived actions. First and second one
        self.assertEqual(
            2, ModerationRequestAction.objects.filter(is_archived=True).count()
        )

        # Now the original author can make amends and resubmit
        self._resubmit_moderation_request(self.author)

        self.assertEqual(200, response.status_code)

        moderation_request.refresh_from_db()
        self.assertTrue(moderation_request.is_active)
        last_action = ModerationRequestAction.objects.last()
        self.assertTrue(last_action.action, constants.ACTION_RESUBMITTED)

        self._approve_moderation_request(self.moderator_1)
        self._approve_moderation_request(self.moderator_2)

        # Back to the content author to either publish or cancel the request
        response = self._cancel_moderation_request(self.author)
        self.assertEqual(200, response.status_code)

        moderation_request.refresh_from_db()
        self.assertFalse(moderation_request.is_active)
        last_action = ModerationRequestAction.objects.last()
        self.assertTrue(last_action.action, constants.ACTION_CANCELLED)
