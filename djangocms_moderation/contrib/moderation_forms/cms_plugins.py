from django.utils.translation import ugettext_lazy as _

from cms.plugin_pool import plugin_pool

from aldryn_forms.cms_plugins import FormPlugin

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

    @classmethod
    def get_child_classes(cls, slot, page, instance=None):
        child_classes = FormPlugin.get_child_classes(slot, page, instance)
        if 'SubmitButton' in child_classes:
            # We don't need the SubmitButton, this plugin is more of a form builder
            child_classes.remove('SubmitButton')
        return child_classes

    def form_valid(self, instance, request, form):
        form.save()


plugin_pool.register_plugin(ModerationFormPlugin)
