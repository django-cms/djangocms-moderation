from unittest.mock import MagicMock

from django import forms
from django.contrib.auth.models import User

from djangocms_moderation import constants
from djangocms_moderation.forms import (
    ModerationRequestForm,
    SelectModerationForm,
    UpdateModerationRequestForm,
)
from djangocms_moderation.models import Workflow

from .utils import BaseTestCase


class ModerationRequestFormTest(BaseTestCase):

    def test_form_init(self):
        form = ModerationRequestForm(
            action=constants.ACTION_STARTED,
            language='en',
            page=self.pg2,
            user=self.user,
            workflow=self.wf1,
            active_request=None,
        )
        self.assertIn('moderator', form.fields)
        field_moderator = form.fields['moderator']
        self.assertEqual(field_moderator.empty_label, 'Any Role 1')
        self.assertQuerysetEqual(field_moderator.queryset, User.objects.none())

    def test_form_save(self):
        data = {
            'moderator': None,
            'message': 'Some message'
        }
        form = ModerationRequestForm(
            data,
            action=constants.ACTION_STARTED,
            language='en',
            page=self.pg2,
            user=self.user,
            workflow=self.wf1,
            active_request=None,
        )
        form.workflow.submit_new_request = MagicMock()
        self.assertTrue(form.is_valid())
        form.save()
        form.workflow.submit_new_request.assert_called_once_with(
            page=self.pg2,
            by_user=self.user,
            to_user=None,
            language='en',
            message='Some message',
        )


class UpdateModerationRequestFormTest(BaseTestCase):

    def test_form_init_approved_action(self):
        form = UpdateModerationRequestForm(
            action=constants.ACTION_APPROVED,
            language='en',
            page=self.pg1,
            user=self.user,
            workflow=self.wf1,
            active_request=self.moderation_request1,
        )
        self.assertIsInstance(form, ModerationRequestForm)
        field_moderator = form.fields['moderator']
        self.assertEqual(field_moderator.empty_label, 'Any Role 2')
        self.assertQuerysetEqual(field_moderator.queryset, User.objects.filter(pk__in=[self.user2.pk]), transform=lambda x: x, ordered=False)

    def test_form_init_cancelled_action(self):
        form = UpdateModerationRequestForm(
            action=constants.ACTION_CANCELLED,
            language='en',
            page=self.pg1,
            user=self.user,
            workflow=self.wf1,
            active_request=self.moderation_request1,
        )
        field_moderator = form.fields['moderator']
        self.assertQuerysetEqual(field_moderator.queryset, User.objects.none())
        self.assertIsInstance(field_moderator.widget, forms.HiddenInput)

    def test_form_init_rejected_action(self):
        form = UpdateModerationRequestForm(
            action=constants.ACTION_REJECTED,
            language='en',
            page=self.pg1,
            user=self.user,
            workflow=self.wf1,
            active_request=self.moderation_request1,
        )
        field_moderator = form.fields['moderator']
        self.assertQuerysetEqual(field_moderator.queryset, User.objects.none())
        self.assertIsInstance(field_moderator.widget, forms.HiddenInput)

    def test_form_save(self):
        data = {
            'moderator': None,
            'message': 'Approved message'
        }
        form = UpdateModerationRequestForm(
            data,
            action=constants.ACTION_APPROVED,
            language='en',
            page=self.pg1,
            user=self.user,
            workflow=self.wf1,
            active_request=self.moderation_request1,
        )
        form.active_request.update_status = MagicMock()
        self.assertTrue(form.is_valid())
        form.save()
        form.active_request.update_status.assert_called_once_with(
            action=constants.ACTION_APPROVED,
            by_user=self.user,
            to_user=None,
            message='Approved message',
        )


class SelectModerationFormTest(BaseTestCase):

    def test_form_init(self):
        form = SelectModerationForm(page=self.pg1,)
        self.assertIn('workflow', form.fields)
        field_workflow = form.fields['workflow']
        self.assertQuerysetEqual(field_workflow.queryset, Workflow.objects.all(), transform=lambda x: x, ordered=False)
        self.assertEqual(field_workflow.initial, self.wf1)
