# -*- coding: utf-8 -*-
from django.utils.translation import ugettext_lazy as _

from cms.toolbar_base import CMSToolbar
from cms.toolbar_pool import toolbar_pool
from cms.api import get_page_draft

from .utils import get_admin_url
from .monkeypatches import set_current_language


class ModerationToolbar(CMSToolbar):
    class Media:
        js = ('djangocms_moderation/js/dist/bundle.moderation.min.js',)
        css = {
            'all': ('djangocms_moderation/css/moderation.css',)
        }

    def __init__(self, *args, **kwargs):
        super(ModerationToolbar, self).__init__(*args, **kwargs)
        set_current_language(self.current_lang)

    def post_template_populate(self):
        super(ModerationToolbar, self).post_template_populate()
        page = get_page_draft(self.request.current_page)
        url = get_admin_url(
            name='item_to_collection',
            language=self.current_lang,
        )
        self.toolbar.add_modal_button(
                name=_('Submit for moderation'),
                url='%s?content_object_id=%s' % (url, page.pk),
                side=self.toolbar.RIGHT,
        )

toolbar_pool.register(ModerationToolbar)
