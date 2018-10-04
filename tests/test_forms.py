import mock

from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.forms import HiddenInput

from djangocms_versioning.models import Version
from djangocms_versioning.test_utils.factories import PageVersionFactory

from djangocms_moderation import constants
from djangocms_moderation.forms import (
    CancelCollectionForm,
    CollectionItemForm,
    CollectionItemsForm,
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


class CollectionItemFormTestCase(BaseTestCase):
    def test_cant_add_to_collection_when_version_lock_is_active(self):
        self.collection1.status = constants.COLLECTING
        self.collection1.save()

        version = PageVersionFactory(created_by=self.user)
        data = {
            'collection': self.collection1.pk,
            'version': version.pk,
        }
        form = CollectionItemForm(data=data, user=version.created_by)
        self.assertTrue(form.is_valid(), form.errors)

        # now lets try to add version locked item
        version = PageVersionFactory(created_by=self.user)
        data = {
            'collection': self.collection1.pk,
            'version': version.pk,
        }
        form = CollectionItemForm(data=data, user=self.user3)
        self.assertFalse(form.is_valid())
        self.assertIn('version', form.errors)

    def test_cant_add_version_which_is_in_moderation(self):
        self.collection1.status = constants.COLLECTING
        self.collection1.save()

        # Version is not a part of any moderation request yet
        version = PageVersionFactory(created_by=self.user)
        data = {
            'collection': self.collection1.pk,
            'version': version.pk,
        }
        form = CollectionItemForm(data=data, user=version.created_by)
        self.assertTrue(form.is_valid(), form.errors)

        # Now lets add the version to an active moderation request
        mr = ModerationRequest.objects.create(
            collection=self.collection1, version=version, is_active=True, author=self.collection1.author
        )
        form = CollectionItemForm(data=data, user=version.created_by)
        self.assertFalse(form.is_valid(), form.errors)
        self.assertIn('version', form.errors)

        # If mr was inactive, we are good to go
        mr.is_active = False
        mr.save()
        form = CollectionItemForm(data=data, user=version.created_by)
        self.assertTrue(form.is_valid(), form.errors)


class CollectionItemsFormTestCase(BaseTestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='test1', email='test1@test.com', password='test1', is_staff=True)
        self.collection_1 = ModerationCollection.objects.create(author=self.user, name='My collection 1',
                                                                workflow=self.wf1)
        self.collection_2 = ModerationCollection.objects.create(author=self.user, name='My collection 2',
                                                                workflow=self.wf1)
        self.content_type = ContentType.objects.get_for_model(self.pg1_version)
        self.pg_version = PageVersionFactory(created_by=self.user)
        self.pg_version_1 = PageVersionFactory(created_by=self.user)

    def test_add_item_to_collection(self):
        ModerationRequest.objects.all().delete()
        data = {
            'collection': self.collection_1.pk,
            'versions': Version.objects.filter(pk__in=[self.pg_version.pk]),
        }
        form = CollectionItemsForm(data=data, user=self.user)
        self.assertTrue(form.is_valid())
        versions = form.clean_versions()
        self.assertQuerysetEqual(
            versions,
            Version.objects.filter(pk__in=[self.pg_version.pk]),
            transform=lambda x: x,
            ordered=False,
        )

    def test_add_items_to_collection(self):
        ModerationRequest.objects.all().delete()
        data = {
            'collection': self.collection_1.pk,
            'versions': [self.pg_version.pk, self.pg_version_1.pk],
        }
        form = CollectionItemsForm(data=data, user=self.user)
        self.assertTrue(form.is_valid())
        versions = form.clean_versions()
        self.assertQuerysetEqual(
            versions,
            Version.objects.filter(pk__in=[self.pg_version.pk, self.pg_version_1.pk]),
            transform=lambda x: x,
            ordered=False,
        )

    def test_attempt_add_with_item_already_in_collection(self):
        data = {
            'collection': self.collection_1.pk,
            'versions': [self.pg1_version.pk, self.pg_version_1.pk],
        }
        form = CollectionItemsForm(data=data, user=self.user)
        self.assertTrue(form.is_valid())
        versions = form.clean_versions()
        self.assertQuerysetEqual(
            versions,
            Version.objects.filter(pk__in=[self.pg_version_1.pk]),
            transform=lambda x: x,
            ordered=False,
        )

    def test_attempt_add_with_all_items_already_in_collection(self):
        data = {
            'collection': self.collection_1.pk,
            'versions': [self.pg1_version.pk, self.pg4_version.pk],
        }
        form = CollectionItemsForm(data=data, user=self.user)
        self.assertFalse(form.is_valid())
        self.assertIn(("All items are locked or are already part of an existing "
                       "moderation request which is part of another active collection"),
                      form.errors['versions'])
