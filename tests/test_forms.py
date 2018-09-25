import mock

from django.contrib.auth.models import User
from django.forms import HiddenInput

from djangocms_moderation import constants
from djangocms_moderation.forms import (
    SubmitCollectionForModerationForm,
    UpdateModerationRequestForm,
    CancelCollectionForm,
)
from djangocms_moderation.models import ModerationCollection

from .utils.base import BaseTestCase


class UpdateModerationRequestFormTest(BaseTestCase):

    def test_form_init_approved_action(self):
        form = UpdateModerationRequestForm(
            action=constants.ACTION_APPROVED,
            language='en',
            page=self.pg1_version,
            user=self.user,
            workflow=self.wf1,
            active_request=self.moderation_request1,
        )
        field_moderator = form.fields['moderator']
        self.assertEqual(field_moderator.empty_label, 'Any Role 2')
        self.assertQuerysetEqual(
            field_moderator.queryset,
            User.objects.filter(pk__in=[self.user2.pk]),
            transform=lambda x: x,
            ordered=False,
        )

    def test_form_init_cancelled_action(self):
        form = UpdateModerationRequestForm(
            action=constants.ACTION_CANCELLED,
            language='en',
            page=self.pg1_version,
            user=self.user,
            workflow=self.wf1,
            active_request=self.moderation_request1,
        )
        field_moderator = form.fields['moderator']
        self.assertQuerysetEqual(field_moderator.queryset, User.objects.none())
        self.assertIsInstance(field_moderator.widget, HiddenInput)

    def test_form_init_rejected_action(self):
        form = UpdateModerationRequestForm(
            action=constants.ACTION_REJECTED,
            language='en',
            page=self.pg1_version,
            user=self.user,
            workflow=self.wf1,
            active_request=self.moderation_request1,
        )
        field_moderator = form.fields['moderator']
        self.assertQuerysetEqual(field_moderator.queryset, User.objects.none())
        self.assertIsInstance(field_moderator.widget, HiddenInput)

    def test_form_save(self):
        data = {
            'moderator': None,
            'message': 'Approved message'
        }
        form = UpdateModerationRequestForm(
            data,
            action=constants.ACTION_APPROVED,
            language='en',
            page=self.pg1_version,
            user=self.user,
            workflow=self.wf1,
            active_request=self.moderation_request1,
        )
        form.active_request.update_status = mock.MagicMock()
        self.assertTrue(form.is_valid())
        form.save()
        form.active_request.update_status.assert_called_once_with(
            action=constants.ACTION_APPROVED,
            by_user=self.user,
            to_user=None,
            message='Approved message',
        )


class SubmitCollectionForModerationFormTest(BaseTestCase):
    @mock.patch.object(ModerationCollection, 'allow_submit_for_review')
    def test_form_is_invalid_if_collection_cant_be_submitted_for_review(self, allow_submit_mock):
        data = {
            'moderator': None,
        }

        allow_submit_mock.return_value = False
        form = SubmitCollectionForModerationForm(
            data,
            collection=self.collection1,
            user=self.user,
        )
        self.assertFalse(form.is_valid())

        allow_submit_mock.return_value = True
        form = SubmitCollectionForModerationForm(
            data,
            collection=self.collection1,
            user=self.user,
        )
        self.assertTrue(form.is_valid())


class CancelCollectionFormTest(BaseTestCase):
    @mock.patch.object(ModerationCollection, 'is_cancellable')
    def test_form_is_invalid_if_collection_cant_be_cancelled(self, is_cancellable_mock):
        is_cancellable_mock.return_value = False
        form = CancelCollectionForm(data={}, collection=self.collection1, user=self.user)
        # Not cancellable
        self.assertFalse(form.is_valid())

        is_cancellable_mock.return_value = True
        form = CancelCollectionForm(data={}, collection=self.collection1, user=self.user)
        self.assertTrue(form.is_valid())
