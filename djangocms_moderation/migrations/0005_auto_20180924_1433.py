# -*- coding: utf-8 -*-
# Generated by Django 1.11.13 on 2018-09-24 13:33
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('djangocms_moderation', '0004_auto_20180907_1206'),
    ]

    operations = [
        migrations.AddField(
            model_name='moderationrequest',
            name='author',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, related_name='+', to=settings.AUTH_USER_MODEL, verbose_name='author'),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='moderationcollection',
            name='author',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='+', to=settings.AUTH_USER_MODEL, verbose_name='moderator'),
        ),
    ]
