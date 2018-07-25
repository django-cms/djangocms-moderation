# -*- coding: utf-8 -*-
from django.utils.translation import ugettext_lazy as _

from cms.api import get_page_draft
from cms.toolbar_base import CMSToolbar
from cms.toolbar_pool import toolbar_pool


class ModerationToolbar(CMSToolbar):
    class Media:
        js = ('djangocms_moderation/js/dist/bundle.moderation.min.js',)
        css = {
            'all': ('djangocms_moderation/css/moderation.css',)
        }

    def __init__(self, *args, **kwargs):
        super(ModerationToolbar, self).__init__(*args, **kwargs)


    def post_template_populate(self):
        super(ModerationToolbar, self).post_template_populate()
        new_request_url = 'http://google.com'

        self.toolbar.add_modal_button(
                name=_('Submit for moderation'),
                url=new_request_url,
                side=self.toolbar.RIGHT,
        )

toolbar_pool.register(ModerationToolbar)
