# -*- coding: utf-8 -*-
# Generated by Django 1.11.12 on 2018-04-12 11:59
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('djangocms_moderation', '0003_pagemoderation_disable_modearation'),
    ]

    operations = [
        migrations.AlterField(
            model_name='workflow',
            name='reference_number_prefix',
            field=models.CharField(blank=True, max_length=3, null=True, verbose_name='reference number prefix'),
        ),
    ]
