# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('djangocms_moderation', '0003_auto_20180417_1727'),
    ]

    operations = [
        migrations.AlterField(
            model_name='pagemoderationrequest',
            name='reference_number',
            field=models.CharField(max_length=32, unique=True),
        ),
    ]
