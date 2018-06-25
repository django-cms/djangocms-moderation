from importlib import import_module
from unittest.mock import patch

from django.conf import settings
from django.test.client import RequestFactory
from django.utils.encoding import force_text

from cms.api import create_page, publish_page
from cms.constants import PUBLISHER_STATE_DIRTY
from cms.middleware.toolbar import ToolbarMiddleware
from cms.toolbar.items import ButtonList, Dropdown, ModalItem
from cms.toolbar.toolbar import CMSToolbar
from cms.utils.conf import get_cms_setting

from djangocms_moderation import constants
from djangocms_moderation.models import PageModeration, PageModerationRequest
from djangocms_moderation.utils import get_admin_url

from .utils import BaseViewTestCase


class BaseToolbarTest(BaseViewTestCase):

    def setup_toolbar(self, page, user, is_edit_mode=True):
        page.set_publisher_state('en', state=PUBLISHER_STATE_DIRTY)  # make page dirty

        if is_edit_mode:
            edit_mode = get_cms_setting('CMS_TOOLBAR_URL__EDIT_ON')
        else:
            edit_mode = get_cms_setting('CMS_TOOLBAR_URL__EDIT_OFF')

        request = RequestFactory().get('{}?{}'.format(page.get_absolute_url('en'), edit_mode))
        request.current_page = page
        request.user = user
        engine = import_module(settings.SESSION_ENGINE)
        request.session = self.client.session
        mid = ToolbarMiddleware().process_request(request)
        self.toolbar = request.toolbar
        self.toolbar.populate()
        self.toolbar.post_template_populate()
        self.toolbar_left_items = self.toolbar.get_left_items()
        self.toolbar_right_items = self.toolbar.get_right_items()


class ExtendedPageToolbarTest(BaseToolbarTest):

    def test_show_publish_button_if_moderation_disabled_for_page(self):
        self.wf1.is_default = False
        self.wf1.save()  # making all workflows not default, therefore by design moderation is disabled
        new_page = create_page(title='New Page', template='page.html', language='en', published=True,)
        self.setup_toolbar(new_page, self.user)
        buttons = sum([item.buttons for item in self.toolbar_right_items if isinstance(item, ButtonList)], [])
        self.assertTrue([button for button in buttons if force_text(button.name) == 'Publish page changes'])

    def test_show_moderation_dropdown_if_moderation_request_non_published_page(self):
        self.setup_toolbar(self.pg1, self.user)
        buttons = sum([item.buttons for item in self.toolbar_right_items if isinstance(item, Dropdown)], [])
        self.assertEqual(len(buttons), 4)
        self.assertEqual(force_text(buttons[0].name), 'Approve changes')
        self.assertEqual(force_text(buttons[1].name), 'Reject changes')
        self.assertEqual(force_text(buttons[2].name), 'Cancel request')
        self.assertEqual(force_text(buttons[3].name), 'View comments')

    def test_show_moderation_dropdown_if_moderation_request_previously_published_page(self):
        # We don't have any fixture for published page in an active moderation
        # request, so let's create one for this test.
        published_page = create_page(
            title='Page 5', template='page.html', language='en', published=True
        )
        moderation_request = PageModerationRequest.objects.create(
            page=published_page, language='en', workflow=self.wf1, is_active=True
        )
        moderation_request.actions.create(
            by_user=self.user, action=constants.ACTION_STARTED
        )
        self.setup_toolbar(published_page, self.user)
        buttons = sum([item.buttons for item in self.toolbar_right_items if isinstance(item, Dropdown)], [])
        self.assertEqual(len(buttons), 5)
        self.assertEqual(force_text(buttons[0].name), 'View differences')
        self.assertEqual(force_text(buttons[1].name), 'Approve changes')
        self.assertEqual(force_text(buttons[2].name), 'Reject changes')
        self.assertEqual(force_text(buttons[3].name), 'Cancel request')
        self.assertEqual(force_text(buttons[4].name), 'View comments')

    def test_show_moderation_dropdown_with_no_actions_for_non_role_user(self):
        self.setup_toolbar(self.pg1, self.user3)
        buttons = sum([item.buttons for item in self.toolbar_right_items if isinstance(item, Dropdown)], [])
        self.assertEqual(len(buttons), 2)
        # `self.pg1` has never been published so we don't show View diff button
        self.assertEqual(force_text(buttons[0].name), 'Cancel request')
        self.assertEqual(force_text(buttons[1].name), 'View comments')

    def test_show_submit_for_moderation_button_if_page_is_dirty(self):
        new_page = create_page(title='New Page', template='page.html', language='en', published=True,)
        self.setup_toolbar(new_page, self.user)
        buttons = sum([item.buttons for item in self.toolbar_right_items if isinstance(item, ButtonList)], [])
        self.assertTrue([button for button in buttons if force_text(button.name) == 'Submit for moderation'])

    def test_submit_for_moderation_button_with_default_settings(self):
        new_page = create_page(title='New Page', template='page.html', language='en', published=True,)
        self.setup_toolbar(new_page, self.user)
        buttons = sum([item.buttons for item in self.toolbar_right_items if isinstance(item, ButtonList)], [])
        submit_for_moderation_button = [
            button for button in buttons if force_text(button.name) == 'Submit for moderation'
        ][0]
        url = get_admin_url(
            name='cms_moderation_new_request',
            language='en',
            args=(new_page.pk, 'en'),
        )
        self.assertEqual(submit_for_moderation_button.url, url)

    @patch('djangocms_moderation.conf.ENABLE_WORKFLOW_OVERRIDE', True)
    def test_submit_for_moderation_button_with_override_settings(self):
        new_page = create_page(title='New Page', template='page.html', language='en', published=True,)
        self.setup_toolbar(new_page, self.user)
        buttons = sum([item.buttons for item in self.toolbar_right_items if isinstance(item, ButtonList)], [])
        submit_for_moderation_button = [
            button for button in buttons if force_text(button.name) == 'Submit for moderation'
        ][0]
        url = get_admin_url(
            name='cms_moderation_select_new_moderation',
            language='en',
            args=(new_page.pk, 'en'),
        )
        self.assertEqual(submit_for_moderation_button.url, url)

    def test_publish_button_after_moderation_request_approved(self):
        self.setup_toolbar(self.pg3, self.user)  # pg3 => moderation request is approved
        publish_page(page=self.pg3, user=self.user, language="en")
        buttons = sum([item.buttons for item in self.toolbar_right_items if isinstance(item, Dropdown)], [])
        self.assertEqual(len(buttons), 2)
        self.assertEqual(force_text(buttons[0].name), 'Publish page changes')
        self.assertEqual(force_text(buttons[1].name), 'Cancel request')


class PageModerationToolbarTest(BaseToolbarTest):

    def test_moderation_menu_add_rendered(self):
        new_page = create_page(title='New Page', template='page.html', language='en',)
        self.setup_toolbar(new_page, self.user)
        page_menu = self.toolbar.menus['page']
        opts = PageModeration._meta
        url = get_admin_url(
            name='{}_{}_{}'.format(opts.app_label, opts.model_name, 'add'),
            language='en',
            args=[],
        )
        url += '?extended_object=%s' % new_page.pk
        self.assertEqual(len(page_menu.find_items(ModalItem, url=url)), 1)

    def test_moderation_menu_change_rendered(self):
        new_page = create_page(title='New Page', template='page.html', language='en',)
        extension = PageModeration.objects.create(extended_object=new_page, enabled=True, workflow=self.wf1,)
        self.setup_toolbar(new_page, self.user)
        page_menu = self.toolbar.menus['page']
        opts = PageModeration._meta
        url = get_admin_url(
            name='{}_{}_{}'.format(opts.app_label, opts.model_name, 'change'),
            language='en',
            args=[extension.pk],
        )
        self.assertEqual(len(page_menu.find_items(ModalItem, url=url)), 1)
