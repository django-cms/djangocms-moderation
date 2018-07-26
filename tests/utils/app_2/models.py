from djangocms_versioning.models import BaseVersion
from django.db import models


class GrouperModel(models.Model):
    content = models.CharField(max_length=255)


class TestModel1(BaseVersion):
    content = models.ForeignKey(GrouperModel)


class TestModel2(BaseVersion):
    content = models.ForeignKey(GrouperModel)
