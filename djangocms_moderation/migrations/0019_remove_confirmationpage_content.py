from django.db import migrations


def _link_placeholders_to_confirmation_pages(apps, schema_editor):
    """Point each placeholder's source field at its confirmation page, so the
    placeholder remains reachable through the PlaceholderRelationField once the
    content foreign key is removed."""
    ContentType = apps.get_model("contenttypes", "ContentType")
    Placeholder = apps.get_model("cms", "Placeholder")
    ConfirmationPage = apps.get_model("djangocms_moderation", "ConfirmationPage")

    content_type, _ = ContentType.objects.get_or_create(
        app_label="djangocms_moderation", model="confirmationpage"
    )
    for confirmation_page in ConfirmationPage.objects.exclude(content__isnull=True):
        Placeholder.objects.filter(pk=confirmation_page.content_id).update(
            content_type=content_type, object_id=confirmation_page.pk
        )


def _unlink_placeholders_from_confirmation_pages(apps, schema_editor):
    ContentType = apps.get_model("contenttypes", "ContentType")
    Placeholder = apps.get_model("cms", "Placeholder")
    ConfirmationPage = apps.get_model("djangocms_moderation", "ConfirmationPage")

    try:
        content_type = ContentType.objects.get(
            app_label="djangocms_moderation", model="confirmationpage"
        )
    except ContentType.DoesNotExist:
        return
    for placeholder in Placeholder.objects.filter(content_type=content_type):
        ConfirmationPage.objects.filter(pk=placeholder.object_id).update(
            content=placeholder
        )


class Migration(migrations.Migration):

    dependencies = [
        ("cms", "0023_placeholder_source_field"),
        ("djangocms_moderation", "0018_alter_collectioncomment_id_and_more"),
    ]

    operations = [
        migrations.RunPython(
            _link_placeholders_to_confirmation_pages,
            _unlink_placeholders_from_confirmation_pages,
        ),
        migrations.RemoveField(
            model_name="confirmationpage",
            name="content",
        ),
    ]
