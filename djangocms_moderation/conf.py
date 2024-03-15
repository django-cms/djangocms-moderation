from django.conf import settings
from django.utils.translation import gettext_lazy as _


UUID_BACKEND = "djangocms_moderation.backends.uuid4_backend"
SEQUENTIAL_NUMBER_BACKEND = "djangocms_moderation.backends.sequential_number_backend"
SEQUENTIAL_NUMBER_WITH_IDENTIFIER_PREFIX_BACKEND = (
    "djangocms_moderation.backends.sequential_number_with_identifier_prefix_backend"
)

CORE_COMPLIANCE_NUMBER_BACKENDS = (
    (UUID_BACKEND, _("Unique alphanumeric string")),
    (SEQUENTIAL_NUMBER_BACKEND, _("Sequential number")),
    (
        SEQUENTIAL_NUMBER_WITH_IDENTIFIER_PREFIX_BACKEND,
        _("Sequential number with identifier prefix"),
    ),
)

DEFAULT_COMPLIANCE_NUMBER_BACKEND = getattr(
    settings, "CMS_MODERATION_DEFAULT_COMPLIANCE_NUMBER_BACKEND", UUID_BACKEND
)

COMPLIANCE_NUMBER_BACKENDS = getattr(
    settings,
    "CMS_MODERATION_COMPLIANCE_NUMBER_BACKENDS",
    CORE_COMPLIANCE_NUMBER_BACKENDS,
)

ENABLE_WORKFLOW_OVERRIDE = getattr(
    settings, "CMS_MODERATION_ENABLE_WORKFLOW_OVERRIDE", False
)

DEFAULT_CONFIRMATION_PAGE_TEMPLATE = getattr(
    settings,
    "CMS_MODERATION_DEFAULT_CONFIRMATION_PAGE_TEMPLATE",
    "djangocms_moderation/moderation_confirmation.html",
)

CORE_CONFIRMATION_PAGE_TEMPLATES = ((DEFAULT_CONFIRMATION_PAGE_TEMPLATE, _("Default")),)

CONFIRMATION_PAGE_TEMPLATES = getattr(
    settings,
    "CMS_MODERATION_CONFIRMATION_PAGE_TEMPLATES",
    CORE_CONFIRMATION_PAGE_TEMPLATES,
)

COLLECTION_COMMENTS_ENABLED = getattr(
    settings, "CMS_MODERATION_COLLECTION_COMMENTS_ENABLED", True
)

REQUEST_COMMENTS_ENABLED = getattr(
    settings, "CMS_MODERATION_REQUEST_COMMENTS_ENABLED", True
)

# If the collection name length is above this limit, it will get truncated
# in the button texts. `None` means no limit
COLLECTION_NAME_LENGTH_LIMIT = getattr(
    settings, "CMS_MODERATION_COLLECTION_NAME_LENGTH_LIMIT", 24
)

EMAIL_NOTIFICATIONS_FAIL_SILENTLY = getattr(
    settings, "EMAIL_NOTIFICATIONS_FAIL_SILENTLY", False
)
