# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations

from djangocms_moderation.utils import call_method_from_string


def populate_reference_number(apps, schema_editor):
    PageModerationRequest = apps.get_model('djangocms_moderation', 'PageModerationRequest')

    for moderation_request in PageModerationRequest.objects.all():
        ref_number = call_method_from_string(moderation_request.workflow.reference_number_backend)
        moderation_request.reference_number = ref_number
        moderation_request.save()


class Migration(migrations.Migration):

    dependencies = [
        ('djangocms_moderation', '0002_auto_20180417_1726'),
    ]

    operations = [
        migrations.RunPython(
            populate_reference_number,
            migrations.RunPython.noop,
        ),
    ]
