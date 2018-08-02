import json
import mock

from django.contrib.auth.models import User
from django.utils.translation import ugettext_lazy as _
from django.urls import reverse

from cms.utils.urlutils import add_url_parameters

from djangocms_moderation import constants
from djangocms_moderation.forms import UpdateModerationRequestForm
from djangocms_moderation.models import (
    ConfirmationFormSubmission,
    ConfirmationPage,
    ModerationCollection)
from djangocms_moderation.utils import get_admin_url

from .utils.base import BaseViewTestCase


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


class SubmitCollectionForModerationViewTest(BaseViewTestCase):
    def setUp(self):
        super(SubmitCollectionForModerationViewTest, self).setUp()
        self.url = reverse(
            'admin:cms_moderation_submit_collection_for_moderation',
            args=(self.collection2.pk,)
        )
        request_change_list_url = reverse('admin:djangocms_moderation_moderationrequest_changelist')
        self.request_change_list_url = "{}?collection__id__exact={}".format(
            request_change_list_url,
            self.collection2.pk
        )

    @mock.patch.object(ModerationCollection, 'submit_for_moderation')
    def test_submit_collection_for_moderation(self, submit_mock):
        response = self.client.get(self.url)
        self.assertEqual(200, response.status_code)

        response = self.client.post(self.url)
        assert submit_mock.called
        self.assertEqual(302, response.status_code)
        self.assertEqual(self.request_change_list_url, response.url)


class ModerationRequestChangeListView(BaseViewTestCase):
    def setUp(self):
        super(ModerationRequestChangeListView, self).setUp()
        self.collection_submit_url = reverse(
            'admin:cms_moderation_submit_collection_for_moderation',
            args=(self.collection2.pk,)
        )
        self.url = reverse('admin:djangocms_moderation_moderationrequest_changelist')
        self.url_with_filter = "{}?collection__id__exact={}".format(
            self.url, self.collection2.pk
        )

    def test_change_list_view_should_contain_collection_object(self):
        response = self.client.get(self.url)
        self.assertEqual(200, response.status_code)
        self.assertNotIn('collection', response.context)

        response = self.client.get(self.url_with_filter)
        self.assertEqual(200, response.status_code)
        self.assertEqual(response.context['collection'], self.collection2)

    @mock.patch.object(ModerationCollection, 'allow_submit_for_moderation')
    def test_change_list_view_should_contain_submit_collection_button(self, allow_submit_mock):
        response = self.client.get(self.url)
        self.assertEqual(200, response.status_code)
        self.assertNotIn('submit_for_moderation_button', response.context)

        allow_submit_mock.__get__ = mock.Mock(return_value=False)
        response = self.client.get(self.url_with_filter)
        self.assertNotIn('submit_for_moderation_button', response.context)

        allow_submit_mock.__get__ = mock.Mock(return_value=True)
        response = self.client.get(self.url_with_filter)
        self.assertIn('submit_for_moderation_button', response.context)
