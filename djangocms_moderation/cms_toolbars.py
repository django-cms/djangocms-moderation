# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.utils.functional import cached_property
from django.utils.translation import override as force_language, ugettext_lazy as _

from cms.api import get_page_draft
from cms.toolbar_pool import toolbar_pool
from cms.toolbar_base import CMSToolbar
from cms.toolbar.items import ModalButton, Dropdown, DropdownToggleButton
from cms.utils.page_permissions import user_can_change_page
from cms.utils.urlutils import admin_reverse

from .helpers import get_page_moderation_workflow
from .models import PageModeration
from .monkeypatches import set_current_language


try:
    PageToolbar = toolbar_pool.toolbars['cms.cms_toolbars.PageToolbar']
except:
    from cms.cms_toolbars import PageToolbar


def _get_admin_url(name, language, args):
    with force_language(language):
        return admin_reverse(name, args=args)


class ExtendedPageToolbar(PageToolbar):

    def __init__(self, *args, **kwargs):
        super(ExtendedPageToolbar, self).__init__(*args, **kwargs)
        set_current_language(self.current_lang)

    @cached_property
    def moderation_request(self):
        workflow = self.moderation_workflow

        if not workflow:
            return None
        return workflow.get_active_request(self.page, self.current_lang)

    @cached_property
    def moderation_workflow(self):
        if not self.page:
            return None
        return get_page_moderation_workflow(self.page)

    def get_cancel_moderation_button(self):
        cancel_request_url = _get_admin_url(
            name='cms_moderation_cancel_request',
            language=self.current_lang,
            args=(self.page.pk, self.current_lang),
        )
        return ModalButton(name=_('Cancel request'), url=cancel_request_url)

    def add_publish_button(self, classes=('cms-btn-action', 'cms-btn-publish', 'cms-btn-publish-active',)):
        page = self.page

        if not self.user_can_publish() or not self.moderation_workflow:
            # Page has no pending changes
            # OR user has no permission to publish
            # OR a moderation workflow has not been defined yet
            return super(ExtendedPageToolbar, self).add_publish_button(classes)

        moderation_request = self.moderation_request

        if moderation_request and moderation_request.is_approved:
            return super(ExtendedPageToolbar, self).add_publish_button(classes)
        elif moderation_request:
            user = self.request.user
            container = Dropdown(side=self.toolbar.RIGHT)
            container.add_primary_button(
                DropdownToggleButton(name=_('Moderation'))
            )

            if moderation_request.user_can_take_action(user):
                approve_request_url = _get_admin_url(
                    name='cms_moderation_approve_request',
                    language=self.current_lang,
                    args=(page.pk, self.current_lang),
                )
                container.buttons.append(
                    ModalButton(name=_('Approve changes'), url=approve_request_url)
                )

            if moderation_request.user_can_take_action(user):
                reject_request_url = _get_admin_url(
                    name='cms_moderation_reject_request',
                    language=self.current_lang,
                    args=(page.pk, self.current_lang),
                )
                container.buttons.append(
                    ModalButton(name=_('Reject changes'), url=reject_request_url)
                )
            container.buttons.append(self.get_cancel_moderation_button())
            self.toolbar.add_item(container)
        else:
            new_request_url = _get_admin_url(
                name='cms_moderation_new_request',
                language=self.current_lang,
                args=(page.pk, self.current_lang),
            )
            self.toolbar.add_modal_button(
                _('Submit for moderation'),
                url=new_request_url,
                side=self.toolbar.RIGHT,
            )

    def get_publish_button(self, classes=None):
        if not self.moderation_workflow:
            return super(ExtendedPageToolbar, self).get_publish_button(classes)

        button = super(ExtendedPageToolbar, self).get_publish_button(['cms-btn-publish'])
        container = Dropdown(side=self.toolbar.RIGHT)
        container.add_primary_button(
            DropdownToggleButton(name=_('Moderation'))
        )
        container.buttons.extend(button.buttons)
        return container


class PageModerationToolbar(CMSToolbar):

    def populate(self):
        # always use draft if we have a page
        page = get_page_draft(self.request.current_page)

        if not page or not user_can_change_page(self.request.user, page):
            return

        page_menu = self.toolbar.get_menu('page')

        if not page_menu or page_menu.disabled:
            return

        try:
            extension = PageModeration.objects.get(extended_object_id=page.pk)
        except PageModeration.DoesNotExist:
            extension = None

        opts = PageModeration._meta

        url_args = []

        if extension:
            url_name = '{}_{}_{}'.format(opts.app_label, opts.model_name, 'change')
            url_args.append(extension.pk)
        else:
            url_name = '{}_{}_{}'.format(opts.app_label, opts.model_name, 'add')

        url = _get_admin_url(url_name, self.current_lang, args=url_args)

        if not extension:
            url += '?extended_object=%s' % page.pk
        not_edit_mode = not self.toolbar.edit_mode_active
        page_menu.add_modal_item(_('Moderation'), url=url, disabled=not_edit_mode)


toolbar_pool.toolbars['cms.cms_toolbars.PageToolbar'] = ExtendedPageToolbar
toolbar_pool.register(PageModerationToolbar)
