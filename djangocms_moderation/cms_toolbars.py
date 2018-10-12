# -*- coding: utf-8 -*-
from django.utils.translation import ugettext_lazy as _

from cms.toolbar_pool import toolbar_pool
from cms.utils.urlutils import add_url_parameters
from cms.cms_toolbars import ADMIN_MENU_IDENTIFIER

from djangocms_versioning.cms_toolbars import VersioningToolbar
from djangocms_versioning.models import Version

from .helpers import (
    get_active_moderation_request,
    get_moderation_button_title_and_url,
    is_obj_review_locked,
    is_obj_version_unlocked,
    is_registered_for_moderation,
)
from .utils import get_admin_url


class ModerationToolbar(VersioningToolbar):
    class Media:
        # Media keeps all the settings from the parent class, so we only need
        # to add moderation media here
        # https://docs.djangoproject.com/en/2.1/topics/forms/media/#extend
        js = (
            'djangocms_moderation/js/dist/bundle.moderation.min.js',
        )
        css = {
            'all': ('djangocms_moderation/css/moderation.css',)
        }

    def _add_publish_button(self):
        """
        Disable djangocms_versioning publish button if we can moderate content object
        """
        if not is_registered_for_moderation(self.toolbar.obj):
            return super()._add_publish_button()

    def _add_edit_button(self, disabled=False):
        """
        Add edit button if we can moderate content object
        Or add a disabled edit button when object is 'Review locked'
        """
        # can we moderate content object?
        # return early to avoid further DB calls below
        if not is_registered_for_moderation(self.toolbar.obj):
            return super()._add_edit_button(disabled=disabled)

        # yes we can! but is it locked?
        if is_obj_review_locked(self.toolbar.obj, self.request.user):
            disabled = True

        # disabled if locked, else default to false
        return super()._add_edit_button(disabled=disabled)

    def _add_moderation_buttons(self):
        """
        Add submit for moderation button if we can moderate content object
        and toolbar is in edit mode

        Display the collection name when object is in moderation
        """
        if not is_registered_for_moderation(self.toolbar.obj):
            return

        if self._is_versioned() and self.toolbar.edit_mode_active:
            moderation_request = get_active_moderation_request(self.toolbar.obj)
            if moderation_request:
                title, url = get_moderation_button_title_and_url(moderation_request)
                self.toolbar.add_sideframe_button(
                    name=title,
                    url=url,
                    side=self.toolbar.RIGHT,
                )
            # Check if the object is not version locked to someone else
            elif is_obj_version_unlocked(self.toolbar.obj, self.request.user):
                version = Version.objects.get_for_content(self.toolbar.obj)
                url = add_url_parameters(
                    get_admin_url(
                        name='cms_moderation_items_to_collection',
                        language=self.current_lang,
                        args=()
                    ),
                    version_ids=version.pk,
                )

                self.toolbar.add_modal_button(
                    name=_('Submit for moderation'),
                    url=url,
                    side=self.toolbar.RIGHT,
                )

    def _add_moderation_menu(self):
        """
        Helper method to add moderation menu in the toolbar
        """
        admin_menu = self.toolbar.get_or_create_menu(ADMIN_MENU_IDENTIFIER)
        url = get_admin_url('djangocms_moderation_moderationcollection_changelist',
                            language=self.current_lang,
                            args=())
        url += '?author__id__exact=%s' % self.request.user.id
        admin_menu.add_link_item(
            _('Moderation collections'),
            url=url,
            position=3
        )

    def post_template_populate(self):
        super().post_template_populate()
        self._add_moderation_buttons()
        self._add_moderation_menu()


toolbar_pool.unregister(VersioningToolbar)
toolbar_pool.register(ModerationToolbar)
