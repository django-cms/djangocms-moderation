from django.test.client import RequestFactory

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

    def _get_toolbar(self, content_obj, edit_mode=False):
        """Helper method to set up the toolbar
        """
        page = PageVersionFactory().content.page
        request = self._get_page_request(
            page=page, user=UserFactory(is_staff=True)
        )
        cms_toolbar = CMSToolbar(request)
        toolbar = ModerationToolbar(
            request, toolbar=cms_toolbar, is_current_app=True, app_path='/')
        toolbar.toolbar.obj = content_obj
        if edit_mode:
            toolbar.toolbar.edit_mode_active = True
            toolbar.toolbar.content_mode_active = False
            toolbar.toolbar.structure_mode_active = False
        return toolbar

    def test_submit_for_moderation(self):
        ModerationRequest.objects.all().delete()
        version = PageVersionFactory()
        toolbar = self._get_toolbar(version.content, edit_mode=True)
        toolbar.populate()
        toolbar.post_template_populate()

        self.assertEquals(
            toolbar.toolbar.get_right_items()[0].buttons[0].name,
            'Submit for moderation'
        )

    def test_page_in_moderation(self):
        ModerationRequest.objects.all().delete()
        version = PageVersionFactory()
        self.collection1.add_version(
            version=version
        )
        toolbar = self._get_toolbar(version.content, edit_mode=True)
        toolbar.populate()
        toolbar.post_template_populate()
        self.assertEquals(
            toolbar.toolbar.get_right_items()[1].buttons[0].name,
            'In Moderation "%s"' % self.collection1.name
        )

    def test_add_edit_button(self):
        ModerationRequest.objects.all().delete()
        version = PageVersionFactory()
        toolbar = self._get_toolbar(version.content)
        toolbar.populate()
        toolbar.post_template_populate()
        # We can see the Edit button, as the version hasn't been submitted
        # to the moderation (collection) yet
        self.assertEquals(
            toolbar.toolbar.get_right_items()[0].buttons[0].name,
            'Edit',
        )
        self.assertFalse(
            toolbar.toolbar.get_right_items()[0].buttons[0].disabled
        )

        # Lets add the version to moderation, the Edit should no longer be
        # clickable
        self.collection1.add_version(
            version=version
        )
        toolbar = self._get_toolbar(version.content)
        toolbar.populate()
        toolbar.post_template_populate()
        self.assertEquals(
            toolbar.toolbar.get_right_items()[0].buttons[0].name,
            'Edit',
        )
        self.assertTrue(
            toolbar.toolbar.get_right_items()[0].buttons[0].disabled
        )
