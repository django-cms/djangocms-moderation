from django.db import migrations, models


def keep_first_default_workflow(apps, schema_editor):
    Workflow = apps.get_model("djangocms_moderation", "Workflow")
    defaults = Workflow.objects.using(schema_editor.connection.alias).filter(is_default=True)
    first = defaults.order_by("name", "pk").first()
    if first is not None:
        defaults.exclude(pk=first.pk).update(is_default=False)


class Migration(migrations.Migration):
    dependencies = [
        ("djangocms_moderation", "0022_alter_moderationcollection_options"),
    ]

    operations = [
        migrations.RunPython(keep_first_default_workflow, migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name="workflow",
            constraint=models.UniqueConstraint(
                fields=["is_default"],
                condition=models.Q(is_default=True),
                name="djangocms_moderation_one_default_workflow",
            ),
        ),
    ]
