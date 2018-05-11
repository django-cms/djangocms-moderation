import json

from django.utils.translation import ugettext_lazy as _

from cms.plugin_pool import plugin_pool

from aldryn_forms.cms_plugins import FormPlugin

from djangocms_moderation.signals import cms_moderation_confirmation_form_submission

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
        cms_moderation_confirmation_form_submission.send(
            sender=self.__class__,
            page_id=request.GET.get('page'),
            language=request.GET.get('language'),
            user=request.user,
            form_data=fields_as_dicts,
        )


plugin_pool.register_plugin(ModerationFormPlugin)
