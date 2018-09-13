# -*- coding: utf-8 -*-
from django.utils.translation import ugettext_lazy as _

from cms.toolbar_pool import toolbar_pool
from cms.utils.urlutils import add_url_parameters

from djangocms_versioning.cms_toolbars import VersioningToolbar
from djangocms_versioning.models import Version

from .models import ModerationRequest
from .utils import get_admin_url, is_obj_review_locked


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
        Disable djangocms_versioning publish button as it needs to go through
        the moderation first
        """
        pass

    def _add_edit_button(self):
        """
        We need to check if the object is not 'Review locked', and only allow
        Edit button if it isn't
        """
        if is_obj_review_locked(self.toolbar.obj, self.request.user):
            # Don't display edit button as the item is Review locked
            # TODO alternatively we could add the edit button using super
            # and mark it as disabled, instead of adding another -disabled one
            self.toolbar.add_modal_button(
                _('Edit'),
                url='#',
                disabled=True,
                side=self.toolbar.RIGHT,
            )
        return super()._add_edit_button()

    def _add_moderation_buttons(self):
        if self._is_versioned() and self.toolbar.edit_mode_active:
            version = Version.objects.get_for_content(self.toolbar.obj)
            try:
                moderation_request = ModerationRequest.objects.get(
                    version=version
                )
                self.toolbar.add_modal_button(
                    name='%s "%s"' % (_('In Moderation'), moderation_request.collection.name),
                    url='#',
                    disabled=True,
                    side=self.toolbar.RIGHT,
                )
            except ModerationRequest.DoesNotExist:
                url = add_url_parameters(
                    get_admin_url(
                        name='cms_moderation_item_to_collection',
                        language=self.current_lang,
                        args=()
                    ),
                    version_id=version.pk
                )

                self.toolbar.add_modal_button(
                    name=_('Submit for moderation'),
                    url=url,
                    side=self.toolbar.RIGHT,
                )

    def post_template_populate(self):
        super().post_template_populate()
        self._add_moderation_buttons()


toolbar_pool.unregister(VersioningToolbar)
toolbar_pool.register(ModerationToolbar)
