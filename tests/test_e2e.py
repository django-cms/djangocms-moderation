from cms.utils.urlutils import admin_reverse
from django.test import TestCase
from django.contrib.auth.models import User

from cms.api import create_page

from djangocms_moderation import constants
from djangocms_moderation.models import (
    Workflow,
    Role,
    PageModerationRequest,
    PageModerationRequestAction,
)
from djangocms_moderation.utils import get_admin_url


class ModerationFlowsTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.workflow = Workflow.objects.create(name='Workflow 1', is_default=True, )

        cls.page = create_page(title='Page 1', template='page.html', language='en', )

        # create users, groups and roles
        cls.author = User.objects.create_superuser(
            username='test1', email='test1@test1.com', password='test1',
        )
        cls.moderator_1 = User.objects.create_superuser(
            username='test2', email='test2@test.com', password='test2',
        )
        cls.moderator_2 = User.objects.create_superuser(
            username='test3', email='test3@test.com', password='test3',
        )

        cls.role1 = Role.objects.create(name='Role 1', user=cls.moderator_1)
        cls.role2 = Role.objects.create(name='Role 2', user=cls.moderator_2)

        cls.step1 = cls.workflow.steps.create(role=cls.role1, is_required=True, order=1)
        cls.step2 = cls.workflow.steps.create(role=cls.role2, is_required=True, order=2)

    def _process_moderation_request(self, user, action, message='Test message'):
        self.client.force_login(user)
        response = self.client.post(
            get_admin_url(
                name='cms_moderation_{}_request'.format(action),
                language='en',
                args=(self.page.pk, 'en')
            ),
            data={'message': message}
        )
        return response

    def _approve_moderation_request(self, user, message='Test message - approved'):
        return self._process_moderation_request(user, 'approve', message)

    def _reject_moderation_request(self, user, message='Test message - rejected'):
        return self._process_moderation_request(user, 'reject', message)

    def _new_moderation_request(self, user, message='Test message - new'):
        return self._process_moderation_request(user, 'new', message)

    def _resubmit_moderation_request(self, user, message='Test message - resubmit'):
        return self._process_moderation_request(user, 'resubmit', message)

    def _cancel_moderation_request(self, user, message='Test message - cancel'):
        return self._process_moderation_request(user, 'cancel', message)

    def test_approve_moderation_workflow(self):
        """
        This case tests the following workflow:
        1. author creates a new moderation request
        2. moderator_1 approves the first stage
        3. moderator_1 tries to approve the second stage - it should not work
        4. moderator_2 approves
        5. author publishes the page and workflow is done
        """
        self.assertFalse(PageModerationRequest.objects.all())
        self.assertFalse(PageModerationRequestAction.objects.all())

        # Lets create a new moderation request
        self._new_moderation_request(self.author)

        moderation_request = PageModerationRequest.objects.get()  # It exists
        action = PageModerationRequestAction.objects.get()
        self.assertEqual(action.action, constants.ACTION_STARTED)

        response = self._approve_moderation_request(self.moderator_1)
        self.assertEqual(response.status_code, 200)

        second_action = PageModerationRequestAction.objects.last()
        self.assertTrue(second_action.action, constants.ACTION_APPROVED)
        self.assertTrue(second_action.message, 'Test message - approved')

        # moderator_1 can't approve the second request, so they will get 403
        response = self._approve_moderation_request(self.moderator_1)
        self.assertEqual(response.status_code, 403)

        # moderator_2 can approve, as per workflow setup
        response = self._approve_moderation_request(self.moderator_2, 'message #2')
        self.assertEqual(response.status_code, 200)

        moderation_request.refresh_from_db()
        self.assertEqual(moderation_request.author, self.author)
        self.assertTrue(moderation_request.is_active)

        third_action = PageModerationRequestAction.objects.last()
        self.assertTrue(third_action.action, constants.ACTION_APPROVED)
        self.assertTrue(second_action.message, 'message #2')

        # Now the original author can publish the changes
        self.client.force_login(self.author)
        self.client.post(
            admin_reverse('cms_page_publish_page', args=(self.page.pk, 'en'))
        )
        moderation_request.refresh_from_db()
        # Moderation request is finished and last action is recorded
        self.assertFalse(moderation_request.is_active)
        last_action = PageModerationRequestAction.objects.last()
        self.assertTrue(last_action.action, constants.ACTION_FINISHED)
        self.assertTrue(moderation_request.reference_number)

    def test_reject_moderation_workflow(self):
        """
        This case tests the following workflow:
        1. author creates a new moderation request
        2. moderator_1 approves the first stage
        3. moderator_2 rejects the changes
        4. author resubmits the amends
        5. all is approved by moderator_1 and moderator_2
        6. author cancels the request

        We would check for the reference number, which should remain the same
        through the whole moderation cycle
        """
        self.assertFalse(PageModerationRequest.objects.all())
        self.assertFalse(PageModerationRequestAction.objects.all())

        # Lets create a new moderation request
        self._new_moderation_request(self.author)

        moderation_request = PageModerationRequest.objects.get()  # It exists
        # make a note of the reference_number as it should not change
        # through the workflow
        reference_number = moderation_request.reference_number

        action = PageModerationRequestAction.objects.get()
        self.assertEqual(action.action, constants.ACTION_STARTED)

        # moderator_1 will approve it now
        response = self._approve_moderation_request(self.moderator_1)
        self.assertEqual(response.status_code, 200)

        # moderator_2 rejects the changes
        response = self._reject_moderation_request(self.moderator_2, 'Please, less swearing')
        self.assertEqual(response.status_code, 200)

        moderation_request.refresh_from_db()
        # Make sure that after the rejection, this moderation request is still active
        self.assertTrue(moderation_request.is_active)

        third_action = PageModerationRequestAction.objects.last()
        self.assertTrue(third_action.action, constants.ACTION_REJECTED)
        self.assertTrue(third_action.message, 'Please, less swearing')

        # Lets check that we now have 2 stale actions. First and second one
        self.assertEqual(2, PageModerationRequestAction.objects.filter(is_stale=True).count())

        # Now the original author can make amends and resubmit
        self._resubmit_moderation_request(self.author)

        self.assertEqual(200, response.status_code)

        moderation_request.refresh_from_db()
        self.assertTrue(moderation_request.is_active)
        last_action = PageModerationRequestAction.objects.last()
        self.assertTrue(last_action.action, constants.ACTION_RESUBMITTED)
        # Check that the reference number is still the same
        self.assertEqual(moderation_request.reference_number, reference_number)

        self._approve_moderation_request(self.moderator_1)
        self._approve_moderation_request(self.moderator_2)

        # Back to the content author to either publish or cancel the request
        response = self._cancel_moderation_request(self.author)
        self.assertEqual(200, response.status_code)

        moderation_request.refresh_from_db()
        self.assertFalse(moderation_request.is_active)
        last_action = PageModerationRequestAction.objects.last()
        self.assertTrue(last_action.action, constants.ACTION_CANCELLED)

        self.assertEqual(moderation_request.reference_number, reference_number)
