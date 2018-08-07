# -*- coding: utf-8 -*-
from django.utils.translation import ugettext_lazy as _

from cms.api import get_page_draft
from cms.toolbar_base import CMSToolbar
from cms.toolbar_pool import toolbar_pool
from cms.utils.urlutils import add_url_parameters

from .utils import get_admin_url


class ModerationToolbar(CMSToolbar):
    class Media:
        js = ('djangocms_moderation/js/dist/bundle.moderation.min.js',)
        css = {
            'all': ('djangocms_moderation/css/moderation.css',)
        }

    def __init__(self, *args, **kwargs):
        super(ModerationToolbar, self).__init__(*args, **kwargs)

    def post_template_populate(self):
        """
        @todo replace page object with generic content object
        :return:
        """
        super(ModerationToolbar, self).post_template_populate()
        page = get_page_draft(self.request.current_page)
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
