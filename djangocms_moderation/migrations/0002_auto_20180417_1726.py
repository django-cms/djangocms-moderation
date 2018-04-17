# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('djangocms_moderation', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='pagemoderation',
            name='enabled',
            field=models.BooleanField(default=True, verbose_name='enable moderation for page'),
        ),
        migrations.AddField(
            model_name='pagemoderationrequest',
            name='reference_number',
            field=models.CharField(blank=True, max_length=32, null=True),
        ),
        migrations.AddField(
            model_name='workflow',
            name='reference_number_backend',
            field=models.CharField(choices=[('djangocms_moderation.backends.default_workflow_reference_number_backend', 'Default')], default='djangocms_moderation.backends.default_workflow_reference_number_backend', max_length=255),
        ),
        migrations.AlterField(
            model_name='pagemoderation',
            name='workflow',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='+', to='djangocms_moderation.Workflow', verbose_name='workflow'),
        ),
        migrations.AlterField(
            model_name='pagemoderationrequest',
            name='language',
            field=models.CharField(choices=[('en', 'en'), ('fr', 'fr')], max_length=5, verbose_name='language'),
        ),
    ]
