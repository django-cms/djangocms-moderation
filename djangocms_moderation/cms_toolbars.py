# -*- coding: utf-8 -*-
from django.contrib.contenttypes.models import ContentType
from django.utils.translation import ugettext_lazy as _

from cms.api import get_page_draft
from cms.toolbar_base import CMSToolbar
from cms.toolbar_pool import toolbar_pool
from cms.utils.urlutils import add_url_parameters

from .utils import get_admin_url
from .models import ModerationRequest


class ModerationToolbar(CMSToolbar):
    class Media:
        js = ('djangocms_moderation/js/dist/bundle.moderation.min.js',)
        css = {
            'all': ('djangocms_moderation/css/moderation.css',)
        }

    def post_template_populate(self):
        """
        @TODO replace page object with generic content object
        :return:
        """
        super(ModerationToolbar, self).post_template_populate()
        page = get_page_draft(self.request.current_page)

        if not page:
            return None

        try:
            content_type = ContentType.objects.get_for_model(page)
            moderation_request = ModerationRequest.objects.get(
                content_type=content_type,
                object_id=page.pk,
            )
            self.toolbar.add_modal_button(
                name=_('In Moderation Collection "%s"' % moderation_request.collection.name),
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
                content_object_id=page.pk
            )

            self.toolbar.add_modal_button(
                name=_('Submit for moderation'),
                url=url,
                side=self.toolbar.RIGHT,
            )


toolbar_pool.register(ModerationToolbar)
