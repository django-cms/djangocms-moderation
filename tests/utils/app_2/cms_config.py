from cms.app_base import CMSAppConfig

from .models import TestModel1, TestModel2


class CMSApp2Config(CMSAppConfig):
    # djangocms_versioning_enabled = True
    # djangocms_moderation_enabled = True
    versioning_models = [TestModel1, TestModel2]
    moderated_models = [TestModel1, TestModel2]

