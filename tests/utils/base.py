from django.contrib.auth.models import Group, User

from cms.test_utils.testcases import CMSTestCase

from djangocms_versioning.constants import PUBLISHED
from djangocms_versioning.test_utils.factories import PageVersionFactory

from djangocms_moderation import constants
from djangocms_moderation.compact import DJANGO_4_1
from djangocms_moderation.models import (
    ModerationCollection,
    ModerationRequest,
    Role,
    Workflow,
)


class MockRequest:
    GET = {}


class AssertQueryMixin:
    """Mixin to append uppercase `assertQuerySetEqual` for TestCase class
    if django version below 4.2
    """

    if DJANGO_4_1:
        def assertQuerySetEqual(self, *args, **kwargs):
            return self.assertQuerysetEqual(*args, **kwargs)


class BaseTestCase(CMSTestCase):
    @classmethod
    def setUpTestData(cls):
        # create workflows
        cls.wf1 = Workflow.objects.create(pk=1, name="Workflow 1", is_default=True)
        cls.wf2 = Workflow.objects.create(pk=2, name="Workflow 2")
        cls.wf3 = Workflow.objects.create(pk=3, name="Workflow 3")
        cls.wf4 = Workflow.objects.create(pk=4, name="Workflow 4")

        # create page versions
        cls.pg1_version = PageVersionFactory()
        cls.pg2_version = PageVersionFactory()
        cls.pg3_version = PageVersionFactory()
        cls.pg4_version = PageVersionFactory(state=PUBLISHED)
        cls.pg5_version = PageVersionFactory()
        cls.pg6_version = PageVersionFactory()

        # create users, groups and roles
        cls.user = User.objects.create_superuser(
            username="test", email="test@test.com", password="test"
        )
        cls.user2 = User.objects.create_superuser(
            username="test2", email="test2@test.com", password="test2"
        )
        cls.user3 = User.objects.create_superuser(
            username="test3", email="test3@test.com", password="test3"
        )

        cls.group = Group.objects.create(name="Group 1")
        cls.user2.groups.add(cls.group)
        cls.user3.groups.add(cls.group)

        cls.role1 = Role.objects.create(name="Role 1", user=cls.user)
        cls.role2 = Role.objects.create(name="Role 2", user=cls.user2)
        cls.role3 = Role.objects.create(name="Role 3", group=cls.group)

        # create workflow steps for workflow
        cls.wf1st1 = cls.wf1.steps.create(role=cls.role1, is_required=True, order=1)
        cls.wf1st2 = cls.wf1.steps.create(role=cls.role2, is_required=False, order=2)
        cls.wf1st3 = cls.wf1.steps.create(role=cls.role3, is_required=True, order=3)

        cls.wf2st1 = cls.wf2.steps.create(role=cls.role1, is_required=True, order=1)
        cls.wf2st2 = cls.wf2.steps.create(role=cls.role3, is_required=True, order=2)

        cls.wf3st1 = cls.wf3.steps.create(role=cls.role1, is_required=True, order=1)
        cls.wf3st2 = cls.wf3.steps.create(role=cls.role3, is_required=False, order=2)

        cls.wf4st4 = cls.wf4.steps.create(role=cls.role1, is_required=True, order=1)

        # create page moderation requests and actions
        cls.collection1 = ModerationCollection.objects.create(
            author=cls.user, name="Collection 1", workflow=cls.wf1
        )
        cls.collection2 = ModerationCollection.objects.create(
            author=cls.user, name="Collection 2", workflow=cls.wf2
        )
        cls.collection3 = ModerationCollection.objects.create(
            author=cls.user, name="Collection 3", workflow=cls.wf3
        )
        cls.collection4 = ModerationCollection.objects.create(
            author=cls.user, name="Collection 4", workflow=cls.wf4
        )
        cls.moderation_request1 = ModerationRequest.objects.create(
            version=cls.pg1_version,
            language="en",
            collection=cls.collection1,
            is_active=True,
            author=cls.collection1.author,
        )
        cls.moderation_request1.actions.create(
            to_user=cls.user2, by_user=cls.user, action=constants.ACTION_STARTED
        )

        ModerationRequest.objects.create(
            version=cls.pg3_version,
            language="en",
            collection=cls.collection1,
            is_active=False,
            author=cls.collection1.author,
        )
        ModerationRequest.objects.create(
            version=cls.pg2_version,
            language="en",
            collection=cls.collection2,
            is_active=False,
            author=cls.collection2.author,
        )

        cls.moderation_request2 = ModerationRequest.objects.create(
            version=cls.pg3_version,
            language="en",
            collection=cls.collection2,
            is_active=True,
            author=cls.collection2.author,
        )
        cls.moderation_request2.actions.create(
            to_user=cls.user2, by_user=cls.user, action=constants.ACTION_STARTED
        )
        cls.moderation_request2.actions.create(
            to_user=cls.user2,
            by_user=cls.user,
            action=constants.ACTION_APPROVED,
            step_approved=cls.wf2st1,
        )
        cls.moderation_request2.actions.create(
            to_user=cls.user2,
            by_user=cls.user,
            action=constants.ACTION_APPROVED,
            step_approved=cls.wf2st2,
        )

        cls.moderation_request3 = ModerationRequest.objects.create(
            version=cls.pg4_version,
            language="en",
            collection=cls.collection3,
            is_active=True,
            author=cls.collection3.author,
        )
        cls.moderation_request3.actions.create(
            to_user=cls.user2, by_user=cls.user, action=constants.ACTION_STARTED
        )
        cls.moderation_request3.actions.create(
            to_user=cls.user2,
            by_user=cls.user,
            action=constants.ACTION_APPROVED,
            step_approved=cls.wf3st1,
        )
        # This request will be rejected
        cls.moderation_request4 = ModerationRequest.objects.create(
            version=cls.pg5_version,
            language="en",
            collection=cls.collection3,
            is_active=True,
            author=cls.collection3.author,
        )
        cls.moderation_request4.actions.create(
            to_user=cls.user2, by_user=cls.user, action=constants.ACTION_STARTED
        )
        cls.moderation_request4.actions.create(
            to_user=cls.user2, by_user=cls.user3, action=constants.ACTION_REJECTED
        )

        cls.moderation_request5 = ModerationRequest.objects.create(
            version=cls.pg6_version,
            language="en",
            collection=cls.collection4,
            is_active=True,
            author=cls.collection4.author,
        )
        cls.moderation_request5.actions.create(
            to_user=cls.user2, by_user=cls.user, action=constants.ACTION_STARTED
        )


class BaseViewTestCase(BaseTestCase):
    def setUp(self):
        self.client.force_login(self.user)
