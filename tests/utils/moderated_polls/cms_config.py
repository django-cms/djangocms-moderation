from cms.app_base import CMSAppConfig
from cms.utils.i18n import get_language_tuple

from djangocms_versioning.datastructures import VersionableItem, default_copy

from .models import PollContent


def get_poll_additional_changelist_action(obj):
    return f"Custom poll link {obj.pk}"


def get_poll_additional_changelist_field(obj):
    version = obj.moderation_request.version

    if hasattr(version, "contentexpiry"):
        return version.contentexpiry.expires
get_poll_additional_changelist_field.short_description = "Expires"


class PollsCMSConfig(CMSAppConfig):
    djangocms_moderation_enabled = True
    # Moderation configuration
    moderated_models = (PollContent,)
    moderation_collection_admin_actions = [get_poll_additional_changelist_action]
    moderation_collection_admin_fields = [get_poll_additional_changelist_field]
    # Versioning configuration
    djangocms_versioning_enabled = True
    versioning = [
        VersionableItem(
            content_model=PollContent,
            grouper_field_name="poll",
            extra_grouping_fields=["language"],
            version_list_filter_lookups={"language": get_language_tuple},
            copy_function=default_copy,
        )
    ]

