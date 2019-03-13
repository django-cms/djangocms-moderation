from cms.app_base import CMSAppConfig

from djangocms_versioning.datastructures import VersionableItem

from .models import App1PostContent, App1TitleContent


class CMSApp1Config(CMSAppConfig):
    djangocms_moderation_enabled = True
    djangocms_versioning_enabled = True
    moderated_models = (App1PostContent, App1TitleContent)

    versioning = [
        VersionableItem(
            content_model=App1PostContent,
            grouper_field_name="post",
            copy_function=lambda x: x,
        ),
        VersionableItem(
            content_model=App1TitleContent,
            grouper_field_name="title",
            copy_function=lambda x: x,
        ),
    ]
