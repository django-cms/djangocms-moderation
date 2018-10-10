import mock

from django.test.client import RequestFactory
from django.urls import reverse

from cms.middleware.toolbar import ToolbarMiddleware
from cms.toolbar.toolbar import CMSToolbar

from djangocms_versioning.test_utils.factories import (
    PageVersionFactory,
    UserFactory,
)

from djangocms_moderation.cms_toolbars import ModerationToolbar
from djangocms_moderation.models import ModerationRequest

from .utils.base import BaseTestCase


class TestCMSToolbars(BaseTestCase):
    def _get_page_request(self, page, user):
        request = RequestFactory().get('/')
        request.session = {}
        request.user = user
        request.current_page = page
        mid = ToolbarMiddleware()
        mid.process_request(request)
        if hasattr(request, 'toolbar'):
            request.toolbar.populate()
        return request

    def _get_toolbar(self, content_obj, user=None, **kwargs):
        """Helper method to set up the toolbar
        """
        if not user:
            user = UserFactory(is_staff=True)
        page = PageVersionFactory().content.page
        request = self._get_page_request(
            page=page, user=user
        )
        cms_toolbar = CMSToolbar(request)
        toolbar = ModerationToolbar(
            request, toolbar=cms_toolbar, is_current_app=True, app_path='/')
        toolbar.toolbar.set_object(content_obj)
        if kwargs.get('edit_mode', False):
            toolbar.toolbar.edit_mode_active = True
            toolbar.toolbar.content_mode_active = False
            toolbar.toolbar.structure_mode_active = False
        elif kwargs.get('structure_mode', False):
            toolbar.toolbar.edit_mode_active = False
            toolbar.toolbar.content_mode_active = False
            toolbar.toolbar.structure_mode_active = True
        elif kwargs.get('preview_mode', False):
            toolbar.toolbar.edit_mode_active = False
            toolbar.toolbar.content_mode_active = True
            toolbar.toolbar.structure_mode_active = False
        return toolbar

    def _find_buttons(self, button_name, toolbar):
        found = []
        for button_list in toolbar.get_right_items():
            found = found + [button for button in button_list.buttons if button.name == button_name]
        return found

    def _button_exists(self, button_name, toolbar):
        found = self._find_buttons(button_name, toolbar)
        return bool(len(found))

    def _find_menu(self, name, toolbar):
        for item in toolbar.get_left_items():
            if item.name == name:
                return item

    def _find_menu_item(self, name, menu):
        name += '...'  # always added to menu items
        for item in menu.items:
            if item.name == name:
                return item

    def test_submit_for_moderation_not_version_locked(self):
        ModerationRequest.objects.all().delete()
        version = PageVersionFactory(created_by=self.user)
        toolbar = self._get_toolbar(version.content, user=self.user, edit_mode=True)
        toolbar.populate()
        toolbar.post_template_populate()

        self.assertTrue(self._button_exists('Submit for moderation', toolbar.toolbar))

    def test_submit_for_moderation_version_locked(self):
        ModerationRequest.objects.all().delete()
        version = PageVersionFactory(created_by=self.user2)
        # Same user to version author is logged in
        toolbar = self._get_toolbar(version.content, user=self.user2, edit_mode=True)
        toolbar.populate()
        toolbar.post_template_populate()

        # Submit for moderation button has been added
        self.assertTrue(self._button_exists('Submit for moderation', toolbar.toolbar))

        # Different user to version author is logged in
        toolbar = self._get_toolbar(version.content, user=self.user, edit_mode=True)
        toolbar.populate()
        toolbar.post_template_populate()

        # No Submit for moderation button has been added
        self.assertFalse(self._button_exists('Submit for moderation', toolbar.toolbar))

    def test_page_in_moderation(self):
        ModerationRequest.objects.all().delete()
        version = PageVersionFactory()
        self.collection1.add_version(version=version)

        toolbar = self._get_toolbar(version.content, edit_mode=True)
        toolbar.populate()
        toolbar.post_template_populate()

        self.assertTrue(self._button_exists('In Moderation "%s"' % self.collection1.name, toolbar.toolbar))

    def test_add_edit_button_with_version_lock(self):
        """
        Version lock is in the test requirements, lets make sure it still works
        with moderation
        """
        ModerationRequest.objects.all().delete()
        # Version created with the same user as toolbar user
        version = PageVersionFactory(created_by=self.user)
        toolbar = self._get_toolbar(version.content, user=self.user)
        toolbar.populate()
        toolbar.post_template_populate()

        self.assertTrue(self._button_exists('Edit', toolbar.toolbar))
        # Edit button should be clickable
        button = self._find_buttons('Edit', toolbar.toolbar)
        self.assertFalse(button[0].disabled)

        # Now version user is different to toolbar user
        version = PageVersionFactory(created_by=self.user2)
        toolbar = self._get_toolbar(version.content, user=self.user)
        toolbar.populate()
        toolbar.post_template_populate()

        self.assertTrue(self._button_exists('Edit', toolbar.toolbar))
        # Edit button should not be clickable
        button = self._find_buttons('Edit', toolbar.toolbar)
        self.assertTrue(button[0].disabled)

    def test_add_edit_button(self):
        ModerationRequest.objects.all().delete()
        version = PageVersionFactory(created_by=self.user)
        toolbar = self._get_toolbar(version.content, user=self.user)
        toolbar.populate()
        toolbar.post_template_populate()

        # We can see the Edit button, as the version hasn't been submitted
        # to the moderation (collection) yet
        self.assertTrue(self._button_exists('Edit', toolbar.toolbar))
        button = self._find_buttons('Edit', toolbar.toolbar)
        self.assertFalse(button[0].disabled)

        # Lets add the version to moderation, the Edit should no longer be
        # clickable
        self.collection1.add_version(version=version)

        # refresh the toolbar
        toolbar = self._get_toolbar(version.content, user=self.user)
        toolbar.populate()
        toolbar.post_template_populate()

        self.assertTrue(self._button_exists('Edit', toolbar.toolbar))
        button = self._find_buttons('Edit', toolbar.toolbar)
        self.assertTrue(button[0].disabled)

    def test_add_edit_button_without_toolbar_object(self):
        ModerationRequest.objects.all().delete()
        toolbar = self._get_toolbar(None)
        toolbar.populate()
        toolbar.post_template_populate()
        # We shouldn't see Edit button when there is no toolbar object set.
        # Some of the custom views in some apps dont have toolbar.obj
        self.assertFalse(self._button_exists('Edit', toolbar.toolbar))

    @mock.patch('djangocms_moderation.cms_toolbars.is_registered_for_moderation')
    def test_publish_buttons_when_unregistered(self, mock_is_registered_for_moderation):
        mock_is_registered_for_moderation.return_value = False
        ModerationRequest.objects.all().delete()
        version = PageVersionFactory()
        toolbar = self._get_toolbar(version.content, edit_mode=True)
        toolbar.populate()
        toolbar.post_template_populate()

        self.assertTrue(self._button_exists('Publish', toolbar.toolbar))

    @mock.patch('djangocms_moderation.cms_toolbars.is_registered_for_moderation')
    def test_add_edit_buttons_when_unregistered(self, mock_is_registered_for_moderation):
        mock_is_registered_for_moderation.return_value = False
        ModerationRequest.objects.all().delete()
        version = PageVersionFactory(created_by=self.user)
        toolbar = self._get_toolbar(version.content, preview_mode=True, user=self.user)
        toolbar.populate()
        toolbar.post_template_populate()

        self.assertTrue(self._button_exists('Edit', toolbar.toolbar))

    def test_add_manage_collection_item_to_moderation_menu(self):
        version = PageVersionFactory(created_by=self.user)
        toolbar = self._get_toolbar(version.content, preview_mode=True, user=self.user)
        toolbar.populate()
        toolbar.post_template_populate()

        moderation_menu = self._find_menu('Moderation', toolbar.toolbar)
        self.assertNotEqual(None, moderation_menu)

        manage_collection_item = self._find_menu_item('Manage Collections', moderation_menu)
        self.assertNotEqual(None, manage_collection_item)

        collection_list_url = reverse('admin:djangocms_moderation_moderationcollection_changelist')
        collection_list_url += "?author__id__exact=%s" % self.user.pk
        self.assertTrue(manage_collection_item.url, collection_list_url)
