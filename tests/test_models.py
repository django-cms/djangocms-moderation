from unittest.mock import MagicMock, patch

from django.contrib.auth.models import User, Group
from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings

from cms.api import create_page

from djangocms_moderation.models import *
from djangocms_moderation import constants
from djangocms_moderation.emails import notify_requested_moderator


class RoleTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username='test', email='test@test.com', password='test', is_staff=True, is_superuser=True)
        cls.user2 = User.objects.create_user(username='test2', email='test2@test.com', password='test2', is_staff=True, is_superuser=True)
        cls.group = Group.objects.create(name='Group 1')
        cls.group2 = Group.objects.create(name='Group 2')
        cls.user.groups.add(cls.group)
        cls.user2.groups.add(cls.group2)

    def test_create_role(self):
        role = Role.objects.create(
            name='Role 1',
            user=self.user
        )
        self.assertEqual(role, Role.objects.get(name='Role 1'))

    def test_user_and_group_validation_error(self):
        role = Role.objects.create(
            name='Role 1',
            user=self.user,
            group=self.group
        )
        self.assertRaisesMessage(ValidationError, 'Can\'t pick both user and group. Only one.', role.clean)

    def test_user_is_assigned(self):
        # with user
        role = Role.objects.create(
            name='Role 1',
            user=self.user
        )
        self.assertTrue(role.user_is_assigned(self.user))
        self.assertFalse(role.user_is_assigned(self.user2))
        # with group
        role = Role.objects.create(
            name='Role 2',
            group=self.group2
        )
        self.assertTrue(role.user_is_assigned(self.user2))
        self.assertFalse(role.user_is_assigned(self.user))

    def test_get_users_queryset(self):
        # with user
        role = Role.objects.create(
            name='Role 1',
            user=self.user
        )
        self.assertQuerysetEqual(role.get_users_queryset(), User.objects.filter(pk=self.user.pk), transform=lambda x: x, ordered=False)
        # with group
        role = Role.objects.create(
            name='Role 2',
            group=self.group2
        )
        self.assertQuerysetEqual(role.get_users_queryset(), User.objects.filter(pk=self.user2.pk), transform=lambda x: x, ordered=False)
