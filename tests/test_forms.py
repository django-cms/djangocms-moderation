import mock

from django.contrib.auth.models import User
from django.forms import HiddenInput

from djangocms_versioning.models import Version
from djangocms_versioning.test_utils.factories import PageVersionFactory

from djangocms_moderation import constants
from djangocms_moderation.forms import (
    CancelCollectionForm,
    CollectionItemsForm,
    ModerationRequestActionInlineForm,
    SubmitCollectionForModerationForm,
    UpdateModerationRequestForm,
)
from djangocms_moderation.models import ModerationCollection, ModerationRequest

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


class ModerationRequestActionInlineFormTest(BaseTestCase):

    def test_non_action_user_cannot_change_comment(self):
        instance = self.moderation_request1.actions.first()
        data = {
            'message': "Some other Message 902630"
        }
        form = ModerationRequestActionInlineForm(data=data, instance=instance)
        form.current_user = User.objects.create_superuser(
            username='non_action_user', email='non_action_user@test.com', password='non_action_user',)
        self.assertFalse(form.is_valid())

    def test_action_user_can_change_own_comment(self):
        instance = self.moderation_request1.actions.first()
        data = {
            'message': "Some other Message 902630"
        }
        form = ModerationRequestActionInlineForm(data=data, instance=instance)
        form.current_user = instance.by_user
        self.assertTrue(form.is_valid())


class CollectionItemsFormTestCase(BaseTestCase):
    def test_add_items_to_collection(self):
        pg_version1 = PageVersionFactory(created_by=self.user)
        pg_version2 = PageVersionFactory(created_by=self.user)
        ModerationRequest.objects.all().delete()
        data = {
            'collection': self.collection1.pk,
            'versions': [pg_version1, pg_version2],
        }
        form = CollectionItemsForm(data=data, user=self.user)
        self.assertTrue(form.is_valid())
        versions = form.clean_versions()
        self.assertQuerysetEqual(
            versions,
            Version.objects.filter(pk__in=[pg_version1.pk, pg_version2.pk]),
            transform=lambda x: x,
            ordered=False,
        )

    def test_attempt_add_with_item_already_in_collection(self):
        pg_version = PageVersionFactory(created_by=self.user)
        data = {
            'collection': self.collection1.pk,
            # pg1_version is part of a collection and will be removed from the form during validation
            'versions': [self.pg1_version, pg_version],
        }
        form = CollectionItemsForm(data=data, user=self.user)
        self.assertTrue(form.is_valid())
        versions = form.clean_versions()
        self.assertQuerysetEqual(
            versions,
            Version.objects.filter(pk__in=[pg_version.pk]),
            transform=lambda x: x,
            ordered=False,
        )

    def test_attempt_add_with_all_items_already_in_collection(self):
        data = {
            'collection': self.collection1.pk,
            # both version objects are part of other collections and will be remove from the form during validation
            'versions': [self.pg1_version, self.pg4_version],
        }
        form = CollectionItemsForm(data=data, user=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn('versions', form.errors)

    def test_attempt_add_version_locked_version(self):
        pg_version_user2 = PageVersionFactory(created_by=self.user2)
        data = {
            'collection': self.collection1.pk,
            # pg_version_user2 is locked by user2 so it will be removed from the form during validation
            'versions': [pg_version_user2],
        }
        form = CollectionItemsForm(data=data, user=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn('versions', form.errors)
