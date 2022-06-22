from cms.app_base import CMSAppConfig
from cms.utils.i18n import get_language_tuple

from djangocms_versioning.datastructures import VersionableItem, default_copy

from .models import NoneModeratedPollContent


class VersionedNoneModeratedAppConfig(CMSAppConfig):
    djangocms_moderation_enabled = False
    djangocms_versioning_enabled = True
    versioning = [
        VersionableItem(
            content_model=NoneModeratedPollContent,
            grouper_field_name="poll",
            extra_grouping_fields=["language"],
            version_list_filter_lookups={"language": get_language_tuple},
            copy_function=default_copy,
        )
    ]
