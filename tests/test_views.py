import json
from mock import patch
from unittest import skip

from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.utils.translation import ugettext_lazy as _

from cms.utils.urlutils import add_url_parameters

from djangocms_moderation import constants
from djangocms_moderation.forms import (
    ItemToCollectionForm,
    ModerationRequestForm,
    UpdateModerationRequestForm,
)
from djangocms_moderation.models import (
    ConfirmationFormSubmission,
    ConfirmationPage,
    ModerationCollection,
    ModerationRequest,
)
from djangocms_moderation.utils import get_admin_url

from .utils.base import BaseViewTestCase


class ItemToCollectionViewTest(BaseViewTestCase):

    def setUp(self):
        from django.contrib.auth.models import User
        self.user = User.objects.create_user(
            username='test1', email='test1@test.com', password='test1', is_staff=True
        )

        self.collection_1 = ModerationCollection.objects.create(
            author=self.user, name='My collection 1', workflow=self.wf1
        )
        self.collection_2 = ModerationCollection.objects.create(
            author=self.user, name='My collection 2', workflow=self.wf1
        )

    def _assert_render(self, response):
        view = response.context_data['view']
        form = response.context_data['form']

        self.assertIsInstance(form, ItemToCollectionForm)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.template_name[0], 'djangocms_moderation/item_to_collection.html')
        self.assertEqual(response.context_data['title'], _('Add to collection'))

    def test_no_collections(self):
        ModerationCollection.objects.all().delete()
        self.client.force_login(self.user)
        response = self.client.get(
            get_admin_url(
                name='item_to_collection',
                language='en',
                args=()
            )
        )

        self._assert_render(response)
        self.assertEqual(list(response.context_data['collection_list']), [])

    def test_collections(self):
        self.client.force_login(self.user)
        response = self.client.get(
            get_admin_url(
                name='item_to_collection',
                language='en',
                args=()
            )
        )

        self._assert_render(response)
        self.assertTrue(self.collection_1 in response.context_data['collection_list'])
        self.assertTrue(self.collection_2 in response.context_data['collection_list'])
        self.assertTrue(2, len(response.context_data['collection_list']))

    def test_add_object_to_collections(self):
        ModerationRequest.objects.all().delete()
        self.client.force_login(self.user)
        response = self.client.post(
            get_admin_url(
                name='item_to_collection',
                language='en',
                args=()
            )
            , {'collection_id':  self.collection_1.pk, 'content_object_id': self.pg1.pk})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'reloadBrowser')

        content_type = ContentType.objects.get_for_model(self.pg1)
        moderation_request = ModerationRequest.objects.filter(
            content_type=content_type,
            object_id=self.pg1.pk,
        )[0]

        self.assertEqual(moderation_request.collection, self.collection_1)

    def test_invalid_content_already_in_collection(self):
        # add object
        self.collection_1._add_object(self.pg1)

        self.client.force_login(self.user)
        response = self.client.post(
            get_admin_url(
                name='item_to_collection',
                language='en',
                args=()
            )
            , {'collection_id': self.collection_1.pk, 'content_object_id': self.pg1.pk})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, _('is already part of existing moderation request which is part'))

    def test_non_existing_content_object(self):
        self.client.force_login(self.user)
        response = self.client.post(
            get_admin_url(
                name='item_to_collection',
                language='en',
                args=()
            )
            , {'collection_id': self.collection_1.pk, 'content_object_id': 9000})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, _('Invalid content_object_id, does not exist'))

    def test_non_existing_collection(self):
        self.client.force_login(self.user)
        response = self.client.post(
            get_admin_url(
                name='item_to_collection',
                language='en',
                args=()
            )
            , {'collection_id': 9000, 'content_object_id': self.pg1.pk})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, _('Collection does not exist'))

    def test_exclude_locked_collections(self):
        ModerationRequest.objects.all().delete()
        self.collection_1.is_locked = True
        self.collection_1.save()

        self.client.force_login(self.user)
        response = self.client.post(
            get_admin_url(
                name='item_to_collection',
                language='en',
                args=()
            )
            , {'collection_id': self.collection_1.pk, 'content_object_id': self.pg1.pk})

        self.assertContains(response, _("because it is locked"))

    def test_list_content_objects_from_first_collection(self):
        ModerationRequest.objects.all().delete()

        collections = ModerationCollection.objects.filter(is_locked=False)
        collections[0]._add_object(self.pg1)
        collections[1]._add_object(self.pg2)

        self.client.force_login(self.user)
        response = self.client.get(
            get_admin_url(
                name='item_to_collection',
                language='en',
                args=()
            )
        )

        moderation_requests = ModerationRequest.objects.filter(collection=collections[0])
        # moderation request is content_object
        for mod_request in moderation_requests:
            self.assertTrue(mod_request in response.context_data['content_object_list'])

    def test_list_content_objects_from_collection_id_param(self):
        ModerationRequest.objects.all().delete()

        self.collection_1._add_object(self.pg1)
        self.collection_2._add_object(self.pg2)

        self.client.force_login(self.user)
        response = self.client.get(
            add_url_parameters(
                get_admin_url(
                    name='item_to_collection',
                    language='en',
                    args=()
                ), collection_id=self.collection_2.pk
            )
        )

        moderation_requests = ModerationRequest.objects.filter(collection=self.collection_2)
        # moderation request is content_object
        for mod_request in moderation_requests:
            self.assertTrue(mod_request in response.context_data['content_object_list'])

    def test_content_object_id_from_params(self):
        self.client.force_login(self.user)
        response = self.client.get(
            add_url_parameters(
                get_admin_url(
                    name='item_to_collection',
                    language='en',
                    args=()
                ), content_object_id=self.pg1.pk
            )
        )

        form = response.context_data['form']
        self.assertEqual(self.pg1.pk, int(form.initial['content_object_id']))

    def test_authenticated_users_only(self):
        response = self.client.get(
            get_admin_url(
                name='item_to_collection',
                language='en',
                args=()
            )
        )

        self.assertEqual(response.status_code, 302)


class ModerationRequestViewTest(BaseViewTestCase):

    def _assert_render(self, response, page, action, workflow, active_request, form_cls, title):
        view = response.context_data['view']
        form = response.context_data['adminform']
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.template_name[0], 'djangocms_moderation/request_form.html')
        self.assertEqual(view.language, 'en')
        self.assertEqual(view.page, page)
        self.assertEqual(view.action, action)
        self.assertEqual(view.workflow, workflow)
        self.assertEqual(view.active_request, active_request)
        self.assertEqual(response.context_data['title'], title)
        self.assertIsInstance(form, form_cls)

    def test_new_request_view_with_form(self):
        response = self.client.get(
            get_admin_url(
                name='cms_moderation_new_request',
                language='en',
                args=(self.pg2.pk, 'en')
            )
        )
        self._assert_render(
            response=response,
            page=self.pg2,
            action=constants.ACTION_STARTED,
            active_request=None,
            workflow=self.wf1,
            form_cls=ModerationRequestForm,
            title=_('Submit for moderation')
        )

    @skip('4.0 rework TBC')
    def test_new_request_view_with_form_workflow_passed_param(self):
        response = self.client.get(
            '{}?{}'.format(
                get_admin_url(
                    name='cms_moderation_new_request',
                    language='en',
                    args=(self.pg2.pk, 'en')
                ),
                'workflow={}'.format(self.wf2.pk)
            )
        )
        self._assert_render(
            response=response,
            page=self.pg2,
            action=constants.ACTION_STARTED,
            active_request=None,
            workflow=self.wf2,
            form_cls=ModerationRequestForm,
            title=_('Submit for moderation')
        )

    def test_cancel_request_view_with_form(self):
        response = self.client.get(get_admin_url(
            name='cms_moderation_cancel_request',
            language='en',
            args=(self.pg1.pk, 'en')
        ))
        self._assert_render(
            response=response,
            page=self.pg1,
            action=constants.ACTION_CANCELLED,
            active_request=self.moderation_request1,
            workflow=self.wf1,
            form_cls=UpdateModerationRequestForm,
            title=_('Cancel request')
        )

    def test_reject_request_view_with_form(self):
        response = self.client.get(get_admin_url(
            name='cms_moderation_reject_request',
            language='en',
            args=(self.pg1.pk, 'en')
        ))
        self._assert_render(
            response=response,
            page=self.pg1,
            action=constants.ACTION_REJECTED,
            active_request=self.moderation_request1,
            workflow=self.wf1,
            form_cls=UpdateModerationRequestForm,
            title=_('Send for rework')
        )

    def test_resubmit_request_view_with_form(self):
        response = self.client.get(get_admin_url(
            name='cms_moderation_resubmit_request',
            language='en',
            args=(self.pg1.pk, 'en')
        ))
        self._assert_render(
            response=response,
            page=self.pg1,
            action=constants.ACTION_RESUBMITTED,
            active_request=self.moderation_request1,
            workflow=self.wf1,
            form_cls=UpdateModerationRequestForm,
            title=_('Resubmit changes')
        )

    def test_approve_request_view_with_form(self):
        response = self.client.get(get_admin_url(
            name='cms_moderation_approve_request',
            language='en',
            args=(self.pg1.pk, 'en')
        ))
        self._assert_render(
            response=response,
            page=self.pg1,
            action=constants.ACTION_APPROVED,
            active_request=self.moderation_request1,
            workflow=self.wf1,
            form_cls=UpdateModerationRequestForm,
            title=_('Approve changes')
        )

    def test_get_form_kwargs(self):
        response = self.client.get(get_admin_url(
            name='cms_moderation_new_request',
            language='en',
            args=(self.pg2.pk, 'en')
        ))
        view = response.context_data['view']
        kwargs = view.get_form_kwargs()
        self.assertEqual(kwargs.get('action'), view.action)
        self.assertEqual(kwargs.get('language'), view.language)
        self.assertEqual(kwargs.get('page'), view.page)
        self.assertEqual(kwargs.get('user'), view.request.user)
        self.assertEqual(kwargs.get('workflow'), view.workflow)
        self.assertEqual(kwargs.get('active_request'), view.active_request)

    @skip('4.0 rework TBC')
    def test_form_valid(self):
        response = self.client.post(get_admin_url(
            name='cms_moderation_new_request',
            language='en',
            args=(self.pg2.pk, 'en')
        ), {'moderator': '', 'message': 'Some review message'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'reloadBrowser')  # check html part

    def test_throws_error_moderation_already_exists(self):
        response = self.client.get('{}?{}'.format(
            get_admin_url(
                name='cms_moderation_new_request',
                language='en',
                args=(self.pg1.pk, 'en')
            ),
            'workflow={}'.format(self.wf1.pk)  # pg1 => active request
        ))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.content, b'Page already has an active moderation request.')

    @skip('4.0 rework TBC')
    def test_throws_error_invalid_workflow_passed(self):
        response = self.client.get('{}?{}'.format(
            get_admin_url(
                name='cms_moderation_new_request',
                language='en',
                args=(self.pg2.pk, 'en')
            ),
            'workflow=10'  # pg2 => no active requests, 10 => workflow does not exist
        ))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.content, b'No moderation workflow exists for page.')

    def test_throws_no_active_moderation_request(self):
        response = self.client.get(get_admin_url(
            name='cms_moderation_cancel_request',
            language='en',
            args=(self.pg2.pk, 'en')  # pg2 => no active requests
        ))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.content, b'Page does not have an active moderation request.')

    def test_throws_error_already_approved(self):
        response = self.client.get(get_admin_url(
            name='cms_moderation_approve_request',
            language='en',
            args=(self.pg3.pk, 'en')  # pg3 => active request with all approved steps
        ))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.content, b'Moderation request has already been approved.')

    def test_throws_error_forbidden_user(self):
        from django.contrib.auth.models import User
        user = User.objects.create_user(username='test1', email='test1@test.com', password='test1', is_staff=True)
        self.client.force_login(user)
        response = self.client.get(get_admin_url(
            name='cms_moderation_approve_request',
            language='en',
            args=(self.pg1.pk, 'en')  # pg1 => active request
        ))
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.content, b'User is not allowed to update request.')

    @patch('djangocms_moderation.views.get_moderation_workflow', return_value=None)
    def test_throws_error_if_workflow_has_not_been_resolved(self, mock_gpmw):
        response = self.client.get(get_admin_url(
            name='cms_moderation_new_request',
            language='en',
            args=(self.pg2.pk, 'en')
        ))
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.content, b'No moderation workflow exists for page.')

    def _create_confirmation_page(self, moderation_request):
        # First delete all the form submissions for the passed moderation_request
        # This will make sure there are no form submissions
        # attached with the passed moderation_request
        moderation_request.form_submissions.all().delete()
        self.cp = ConfirmationPage.objects.create(
            name='Checklist Form',
        )
        self.role1.confirmation_page = self.cp
        self.role1.save()

    def test_redirects_to_confirmation_page_if_invalid_check(self):
        self._create_confirmation_page(self.moderation_request1)
        response = self.client.get(
            get_admin_url(
                name='cms_moderation_approve_request',
                language='en',
                args=(self.pg1.pk, 'en')
            )
        )
        redirect_url = add_url_parameters(
            self.cp.get_absolute_url(),
            content_view=True,
            page=self.pg1.pk,
            language='en',
        )
        self.assertEqual(response.status_code, 302)  # redirection
        self.assertEqual(response.url, redirect_url)

    def test_does_not_redirect_to_confirmation_page_if_valid_check(self):
        self._create_confirmation_page(self.moderation_request1)
        ConfirmationFormSubmission.objects.create(
            request=self.moderation_request1,
            for_step=self.wf1st1,
            by_user=self.user,
            data=json.dumps([{'label': 'Question 1', 'answer': 'Yes'}]),
            confirmation_page=self.cp,
        )
        response = self.client.get(
            get_admin_url(
                name='cms_moderation_approve_request',
                language='en',
                args=(self.pg1.pk, 'en')
            )
        )
        self._assert_render(
            response=response,
            page=self.pg1,
            action=constants.ACTION_APPROVED,
            active_request=self.moderation_request1,
            workflow=self.wf1,
            form_cls=UpdateModerationRequestForm,
            title=_('Approve changes')
        )

    def test_renders_all_form_submissions(self):
        self._create_confirmation_page(self.moderation_request1)
        ConfirmationFormSubmission.objects.create(
            request=self.moderation_request1,
            for_step=self.wf1st1,
            by_user=self.user,
            data=json.dumps([{'label': 'Question 1', 'answer': 'Yes'}]),
            confirmation_page=self.cp,
        )
        response = self.client.get(
            get_admin_url(
                name='cms_moderation_approve_request',
                language='en',
                args=(self.pg1.pk, 'en')
            )
        )
        form_submissions = response.context_data['form_submissions']
        results = ConfirmationFormSubmission.objects.filter(request=self.moderation_request1)
        self.assertQuerysetEqual(form_submissions, results, transform=lambda x: x, ordered=False)


class ModerationCommentsViewTest(BaseViewTestCase):

    def test_comment_list(self):
        response = self.client.get(
            get_admin_url(
                name='cms_moderation_comments',
                language='en',
                args=(self.pg3.pk, 'en')
            )
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context_data['object_list'].count(), 3)

    def test_comment_list_protected(self):
        new_user = User.objects.create_superuser(
            username='new_user', email='new_user@test.com', password='test'
        )
        self.client.force_login(new_user)

        response = self.client.get(
            get_admin_url(
                name='cms_moderation_comments',
                language='en',
                args=(self.pg3.pk, 'en')
            )
        )

        self.assertEqual(response.status_code, 403)


class ModerationConfirmationPageTest(BaseViewTestCase):

    def setUp(self):
        super(ModerationConfirmationPageTest, self).setUp()
        self.cp = ConfirmationPage.objects.create(
            name='Checklist Form',
        )

    def test_renders_build_view(self):
        response = self.client.get(self.cp.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.templates[0].name, self.cp.template)
        self.assertEqual(
            response.context['CONFIRMATION_BASE_TEMPLATE'],
            'djangocms_moderation/base_confirmation_build.html',
        )

    def test_renders_content_view(self):
        response = self.client.get(
            add_url_parameters(
                self.cp.get_absolute_url(),
                content_view=True,
                page=self.pg1.pk,
                language='en',
            )
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.templates[0].name, self.cp.template)
        self.assertEqual(response.context['CONFIRMATION_BASE_TEMPLATE'], 'djangocms_moderation/base_confirmation.html')

    def test_renders_post_view(self):
        response = self.client.post(
            add_url_parameters(
                self.cp.get_absolute_url(),
                content_view=True,
                page=self.pg1.pk,
                language='en',
            )
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.templates[0].name, self.cp.template)
        self.assertEqual(response.context['CONFIRMATION_BASE_TEMPLATE'], 'djangocms_moderation/base_confirmation.html')
        self.assertTrue(response.context['submitted'])
        redirect_url = add_url_parameters(
            get_admin_url(
                name='cms_moderation_approve_request',
                language='en',
                args=(self.pg1.pk, 'en'),
            ),
            reviewed=True,
        )
        self.assertEqual(response.context['redirect_url'], redirect_url)
