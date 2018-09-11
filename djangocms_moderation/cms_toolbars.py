# -*- coding: utf-8 -*-
from django.utils.translation import ugettext_lazy as _

from cms.toolbar_pool import toolbar_pool
from cms.utils.urlutils import add_url_parameters

from djangocms_versioning.cms_toolbars import VersioningToolbar
from djangocms_versioning.models import Version

from .models import ModerationRequest
from .utils import get_admin_url


class ModerationToolbar(VersioningToolbar):
    class Media:
        js = ('djangocms_moderation/js/dist/bundle.moderation.min.js',
              'djangocms_versioning/js/actions.js',)
        css = {
            'all': ('djangocms_moderation/css/moderation.css',)
        }

    def _add_publish_button(self):
        """
        Override djangocms_versioning publish button
        """
        pass

    def post_template_populate(self):
        super().post_template_populate()

        if self._is_versioned():
            version = Version.objects.get_for_content(self.toolbar.obj)
            try:
                moderation_request = ModerationRequest.objects.get(
                    version=version
                )
                self.toolbar.add_modal_button(
                    name=_('In Moderation "%s"' % moderation_request.collection.name),
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


toolbar_pool.unregister(VersioningToolbar)
toolbar_pool.register(ModerationToolbar)
