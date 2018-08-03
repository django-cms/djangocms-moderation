from cms.app_base import CMSAppConfig

from djangocms_versioning.datastructures import VersionableItem

from .models import App2TitleContent, App2PostContent


class CMSApp1Config(CMSAppConfig):
    djangocms_moderation_enabled = True
    djangocms_versioning_enabled = True
    moderated_models = (App2PostContent, App2TitleContent)

    versioning = [
        VersionableItem(
            content_model=App2PostContent,
            grouper_field_name='post'
        ),
        VersionableItem(
            content_model=App2TitleContent,
            grouper_field_name='title'
        )
    ]


