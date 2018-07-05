# -*- coding: utf-8 -*-
# Generated by Django 1.11.13 on 2018-07-03 13:00
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('djangocms_moderation', '0006_auto_20180618_2102'),
    ]

    operations = [
        migrations.RenameField(
            model_name='workflow',
            old_name='reference_number_backend',
            new_name='compliance_number_backend',
        ),
        migrations.RemoveField(
            model_name='pagemoderationrequest',
            name='reference_number',
        ),
        migrations.AddField(
            model_name='pagemoderationrequest',
            name='compliance_number',
            field=models.CharField(blank=True, max_length=32, null=True, unique=True),
        ),
        migrations.AddField(
            model_name='workflow',
            name='identifier',
            field=models.CharField(blank=True, default='', help_text="Identifier is a 'free' field you could use for internal purposes. For example, it could be used as a workflow specific prefix of a compliance number", max_length=128),
        ),
        migrations.AddField(
            model_name='workflow',
            name='requires_compliance_number',
            field=models.BooleanField(default=False, help_text='Does the Compliance number need to be generated before the moderation request is approved? Please select the compliance number backend bellow'),
            field=models.BooleanField(default=False, help_text='Does the Compliance number need to be generated before the moderation request is approved? Please select the compliance number backend below'),
        ),
    ]
