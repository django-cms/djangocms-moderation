from django.conf import settings
from django.utils.translation import override as force_language, ugettext_lazy as _


DEFAULT_REFERENCE_NUMBER_BACKEND = 'djangocms_moderation.backends.uuid4_backend'

CORE_REFERENCE_NUMBER_BACKENDS = (
    (DEFAULT_REFERENCE_NUMBER_BACKEND, _('Default')),
)

REFERENCE_NUMBER_BACKENDS = getattr(settings, 'CMS_MODERATION_REFERENCE_NUMBER_BACKENDS', CORE_REFERENCE_NUMBER_BACKENDS)

ENABLE_WORKFLOW_OVERRIDE = getattr(settings, 'CMS_MODERATION_ENABLE_WORKFLOW_OVERRIDE', False)
