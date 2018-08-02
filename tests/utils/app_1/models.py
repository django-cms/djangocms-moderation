from django.db import models


class GrouperModel(models.Model):
    content = models.CharField(max_length=255)


class TestModel3(models.Model):
    content = models.ForeignKey(GrouperModel)


class TestModel4(models.Model):
    content = models.ForeignKey(GrouperModel)
