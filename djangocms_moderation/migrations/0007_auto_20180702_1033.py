# -*- coding: utf-8 -*-
# Generated by Django 1.11.13 on 2018-07-02 09:33
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('djangocms_moderation', '0006_auto_20180618_2102'),
    ]

    operations = [
        migrations.RenameField(
            model_name='pagemoderationrequest',
            old_name='reference_number',
            new_name='compliance_number',
        ),
        migrations.RenameField(
            model_name='workflow',
            old_name='reference_number_backend',
            new_name='compliance_number_backend',
        ),
        migrations.AddField(
            model_name='workflow',
            name='identifier',
            field=models.CharField(blank=True, default='', max_length=128),
        ),
        migrations.AddField(
            model_name='workflow',
            name='requires_compliance_number',
            field=models.BooleanField(default=False, help_text='Does the Compliance number need to be generated before the moderation request is approved? Please select the compliance number backend bellow'),
        ),
    ]