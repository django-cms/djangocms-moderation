# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('cms', '0016_auto_20160608_1535'),
        ('auth', '0006_require_contenttypes_0002'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='PageModeration',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('grant_on', models.IntegerField(default=5, verbose_name='grant on', choices=[(1, 'Current page'), (2, 'Page children (immediate)'), (3, 'Page and children (immediate)'), (4, 'Page descendants'), (5, 'Page and descendants')])),
                ('extended_object', models.OneToOneField(editable=False, to='cms.Page')),
                ('public_extension', models.OneToOneField(related_name='draft_extension', null=True, editable=False, to='djangocms_moderation.PageModeration')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='PageModerationRequest',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('language', models.CharField(max_length=5, verbose_name='language', choices=settings.LANGUAGES)),
                ('is_active', models.BooleanField(default=False, db_index=True)),
                ('date_sent', models.DateTimeField(auto_now_add=True, verbose_name='date sent')),
                ('page', models.ForeignKey(verbose_name='page', to='cms.Page')),
            ],
            options={
                'verbose_name': 'Request',
                'verbose_name_plural': 'Requests',
            },
        ),
        migrations.CreateModel(
            name='PageModerationRequestAction',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('action', models.CharField(max_length=30, verbose_name='status', choices=[('start', 'Started'), ('rejected', 'Rejected'), ('approved', 'Approved'), ('cancelled', 'Cancelled'), ('finished', 'Finished')])),
                ('message', models.TextField(verbose_name='message', blank=True)),
                ('date_taken', models.DateTimeField(auto_now_add=True, verbose_name='date taken')),
                ('by_user', models.ForeignKey(related_name='+', verbose_name='by user', to=settings.AUTH_USER_MODEL)),
                ('request', models.ForeignKey(related_name='actions', verbose_name='request', to='djangocms_moderation.PageModerationRequest')),
            ],
            options={
                'ordering': ('date_taken',),
                'verbose_name': 'Action',
                'verbose_name_plural': 'Actions',
            },
        ),
        migrations.CreateModel(
            name='Role',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=120, verbose_name='name')),
                ('group', models.ForeignKey(verbose_name='group', blank=True, to='auth.Group', null=True)),
                ('user', models.ForeignKey(verbose_name='user', blank=True, to=settings.AUTH_USER_MODEL, null=True)),
            ],
            options={
                'verbose_name': 'Role',
                'verbose_name_plural': 'Roles',
            },
        ),
        migrations.CreateModel(
            name='Workflow',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(unique=True, max_length=120, verbose_name='name')),
                ('is_default', models.BooleanField(default=False, verbose_name='is default')),
            ],
            options={
                'verbose_name': 'Workflow',
                'verbose_name_plural': 'Workflows',
            },
        ),
        migrations.CreateModel(
            name='WorkflowStep',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('is_required', models.BooleanField(default=True, verbose_name='is mandatory')),
                ('order', models.PositiveIntegerField()),
                ('role', models.ForeignKey(related_name='+', verbose_name='role', to='djangocms_moderation.Role')),
                ('workflow', models.ForeignKey(related_name='steps', verbose_name='workflow', to='djangocms_moderation.Workflow')),
            ],
            options={
                'ordering': ('order',),
                'verbose_name': 'Step',
                'verbose_name_plural': 'Steps',
            },
        ),
        migrations.AddField(
            model_name='pagemoderationrequestaction',
            name='step_approved',
            field=models.ForeignKey(verbose_name='step approved', blank=True, to='djangocms_moderation.WorkflowStep', null=True),
        ),
        migrations.AddField(
            model_name='pagemoderationrequestaction',
            name='to_role',
            field=models.ForeignKey(related_name='+', verbose_name='to role', blank=True, to='djangocms_moderation.Role', null=True),
        ),
        migrations.AddField(
            model_name='pagemoderationrequestaction',
            name='to_user',
            field=models.ForeignKey(related_name='+', verbose_name='to user', blank=True, to=settings.AUTH_USER_MODEL, null=True),
        ),
        migrations.AddField(
            model_name='pagemoderationrequest',
            name='workflow',
            field=models.ForeignKey(related_name='requests', verbose_name='workflow', to='djangocms_moderation.Workflow'),
        ),
        migrations.AddField(
            model_name='pagemoderation',
            name='workflow',
            field=models.ForeignKey(related_name='+', verbose_name='workflow', to='djangocms_moderation.Workflow'),
        ),
        migrations.AlterUniqueTogether(
            name='workflowstep',
            unique_together=set([('role', 'workflow')]),
        ),
    ]
