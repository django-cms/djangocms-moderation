from django.utils.translation import ugettext_lazy as _

from aldryn_forms.models import FormPlugin


class ModerationForm(FormPlugin):

    class Meta:
        proxy = True
        verbose_name = _('Moderation Form')
        verbose_name_plural = _('Moderation Forms')
