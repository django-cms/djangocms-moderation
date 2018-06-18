import json

from django.utils.translation import ugettext_lazy as _

from cms.plugin_pool import plugin_pool

from aldryn_forms.cms_plugins import FormPlugin

from djangocms_moderation.signals import confirmation_form_submission
from djangocms_moderation.helpers import get_page_or_404

from .models import ModerationForm


class ModerationFormPlugin(FormPlugin):
    name = _('Moderation Form')
    model = ModerationForm
    fieldsets = (
        (None, {
            'fields': (
                'name',
            ),
        }),
    )

    def form_valid(self, instance, request, form):
        fields = form.get_serialized_fields(is_confirmation=False)
        fields_as_dicts = [field._asdict() for field in fields]
        page = get_page_or_404(request.GET.get('page'), request.GET.get('language'))

        confirmation_form_submission.send(
            sender=self.__class__,
            page=page,
            language=request.GET.get('language'),
            user=request.user,
            form_data=fields_as_dicts,
        )


plugin_pool.register_plugin(ModerationFormPlugin)
