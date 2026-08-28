import django.db.models.deletion
from django.db import migrations, models


def populate_parent(apps, schema_editor):
    """
    Derive the parent of every node from its materialized path.

    django-treebeard keeps the tree in ``path`` alone, so existing rows have no
    parent to migrate over. The CMS core tree backend treats the ``parent``
    foreign key as the source of truth, hence the backfill.

    Nodes whose ancestor row is missing (a tree left dangling by an earlier
    treebeard-unaware cascade delete) keep a ``NULL`` parent and are thereby
    turned into roots.
    """
    ModerationRequestTreeNode = apps.get_model(
        'djangocms_moderation', 'ModerationRequestTreeNode'
    )
    nodes = ModerationRequestTreeNode.objects.using(schema_editor.connection.alias)
    pk_by_path = dict(nodes.values_list('path', 'pk'))

    updated = []
    for node in nodes.exclude(depth=1).only('pk', 'path', 'depth'):
        # Path segments are fixed width, one per level, so cutting the last
        # segment off yields the parent's path, whatever ``steplen`` was in use.
        steplen = len(node.path) // node.depth
        node.parent_id = pk_by_path.get(node.path[:-steplen])
        updated.append(node)

    nodes.bulk_update(updated, ['parent'], batch_size=500)


class Migration(migrations.Migration):

    dependencies = [
        ('djangocms_moderation', '0020_moderationcollection_action'),
    ]

    operations = [
        migrations.AddField(
            model_name='moderationrequesttreenode',
            name='parent',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='children', to='djangocms_moderation.moderationrequesttreenode', verbose_name='parent'),
        ),
        migrations.RunPython(populate_parent, migrations.RunPython.noop, elidable=True),
    ]
