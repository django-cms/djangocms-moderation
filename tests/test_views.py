from django.test import TestCase, override_settings

from djangocms_moderation.views import *
from djangocms_moderation.forms import SelectModerationForm

from .utils import BaseDataTestCase, get_admin_url


class SelectModerationViewTest(BaseDataTestCase):

    def test_renders_view_with_form(self):
        self.client.force_login(self.user)
        response = self.client.get(get_admin_url(
            name='cms_moderation_select_new_moderation',
            language='en',
            args=(self.pg1.pk, 'en')
        ))
        view = response.context_data['view']
        form = response.context_data['adminform']
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.template_name[0], 'djangocms_moderation/select_workflow_form.html')
        self.assertEqual(view.page_id, str(self.pg1.pk))
        self.assertEqual(view.current_lang, 'en')
        self.assertIsInstance(form, SelectModerationForm)

        # test form kwargs
        kwargs = view.get_form_kwargs()
        self.assertEqual(kwargs.get('page'), self.pg1)

    def test_form_valid(self):
        self.client.force_login(self.user)
        response = self.client.post(get_admin_url(
            name='cms_moderation_select_new_moderation',
            language='en',
            args=(self.pg1.pk, 'en')
        ), {'workflow': self.wf2.pk})
        form_valid_redirect_url = get_admin_url(
            name='cms_moderation_new_request',
            language='en',
            args=(self.pg1.pk, 'en', self.wf2.pk)
        )
        self.assertEqual(response.url, form_valid_redirect_url)
