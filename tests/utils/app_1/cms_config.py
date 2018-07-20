from cms.app_base import CMSAppConfig

from .models import TestModel3, TestModel4


class CMSApp1Config(CMSAppConfig):
    django_versioning_enabled = True
    djangocms_moderation_enabled = True
    versioning_models = [TestModel3, TestModel4]
    moderated_models = [TestModel3, TestModel4]

