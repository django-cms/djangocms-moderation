from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("djangocms_moderation", "0019_remove_confirmationpage_content"),
    ]

    operations = [
        migrations.AddField(
            model_name="moderationcollection",
            name="action",
            field=models.CharField(
                choices=[("publish", "Publish"), ("unpublish", "Unpublish")],
                db_index=True,
                default="publish",
                help_text=(
                    "Whether approving this collection publishes its content or "
                    "unpublishes it. The review workflow is the same for both."
                ),
                max_length=10,
                verbose_name="action",
            ),
        ),
    ]
