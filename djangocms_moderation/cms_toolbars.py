# -*- coding: utf-8 -*-
from django.utils.translation import ugettext_lazy as _

from cms.toolbar_base import CMSToolbar
from cms.toolbar_pool import toolbar_pool
from cms.utils.urlutils import add_url_parameters

from djangocms_versioning.models import Version

from .models import ModerationRequest
from .utils import get_admin_url


class ModerationToolbar(CMSToolbar):
    class Media:
        js = ('djangocms_moderation/js/dist/bundle.moderation.min.js',)
        css = {
            'all': ('djangocms_moderation/css/moderation.css',)
        }

    def post_template_populate(self):
        super().post_template_populate()
        # TODO replace page object with generic content object
        page = self.request.current_page

        if not page:
            return None

        try:
            # TODO Make this work with the correct version
            version = Version.objects.get(pk=9999)
            moderation_request = ModerationRequest.objects.get(
                version=version
            )
            self.toolbar.add_modal_button(
                name=_('In Moderation "%s"' % moderation_request.collection.name),
                url='#',
                disabled=True,
                side=self.toolbar.RIGHT,
            )
        except (ModerationRequest.DoesNotExist, Version.DoesNotExist):
            url = add_url_parameters(
                get_admin_url(
                    name='cms_moderation_item_to_collection',
                    language=self.current_lang,
                    args=()
                ),
                content_object_id=page.pk
            )

            self.toolbar.add_modal_button(
                name=_('Submit for moderation'),
                url=url,
                side=self.toolbar.RIGHT,
            )


toolbar_pool.register(ModerationToolbar)
