from django.test.client import RequestFactory

from cms.middleware.toolbar import ToolbarMiddleware
from cms.toolbar.toolbar import CMSToolbar
from cms.utils.conf import get_cms_setting

from djangocms_moderation.cms_toolbars import ModerationToolbar
from djangocms_moderation.models import ModerationRequest
from djangocms_versioning.test_utils.factories import (
    PageVersionFactory,
    UserFactory,
)

from .utils.base import BaseTestCase


class TestCMSToolbars(BaseTestCase):

    def get_page_request(self, page, user, path=None, edit=False,
                         preview=False, structure=False, lang_code='en', disable=False):
        if not path:
            path = page.get_absolute_url()

        if edit:
            path += '?%s' % get_cms_setting('CMS_TOOLBAR_URL__EDIT_ON')

        if structure:
            path += '?%s' % get_cms_setting('CMS_TOOLBAR_URL__BUILD')

        if preview:
            path += '?preview'

        request = RequestFactory().get(path)
        request.session = {}
        request.user = user
        request.LANGUAGE_CODE = lang_code
        if edit:
            request.GET = {'edit': None}
        else:
            request.GET = {'edit_off': None}
        if disable:
            request.GET[get_cms_setting('CMS_TOOLBAR_URL__DISABLE')] = None
        request.current_page = page
        mid = ToolbarMiddleware()
        mid.process_request(request)
        if hasattr(request, 'toolbar'):
            request.toolbar.populate()
        return request

    def _get_toolbar(self, content_obj, **kwargs):
        """Helper method to set up the toolbar
        """
        request = RequestFactory().get('/')
        request.user = UserFactory()
        request.session = {}
        cms_toolbar = CMSToolbar(request)
        toolbar = ModerationToolbar(
            request, toolbar=cms_toolbar, is_current_app=True, app_path='/')
        toolbar.toolbar.obj = content_obj
        if kwargs.get('edit_mode', False):
            toolbar.toolbar.edit_mode_active = True
            toolbar.toolbar.content_mode_active = False
            toolbar.toolbar.structure_mode_active = False
        elif kwargs.get('preview_mode', False):
            toolbar.toolbar.edit_mode_active = False
            toolbar.toolbar.content_mode_active = True
            toolbar.toolbar.structure_mode_active = False
        elif kwargs.get('structure_mode', False):
            toolbar.toolbar.edit_mode_active = False
            toolbar.toolbar.content_mode_active = False
            toolbar.toolbar.structure_mode_active = True
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
            toolbar.toolbar.get_right_items()[0].buttons[0].name,
            'In Moderation "%s"' % self.collection1.name
        )
