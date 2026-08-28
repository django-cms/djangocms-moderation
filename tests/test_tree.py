from importlib import import_module
from types import SimpleNamespace

from django.apps import apps
from django.contrib import admin
from django.db import connection
from django.test import TestCase
from django.urls import reverse

from cms.test_utils.testcases import CMSTestCase

from djangocms_moderation.admin import ModerationRequestTreeAdmin
from djangocms_moderation.models import ModerationRequestTreeNode
from djangocms_moderation.tree import BASE_MAINTAINS_PARENT, TreeNodeBase, get_tree_backend

from .utils import factories


class TreeBackendTestCase(TestCase):
    """
    The tree implementation follows the ``CMS_TREE_BACKEND`` setting the CMS
    core resolves, so the moderation tree does not depend on treebeard in a
    project that runs the page tree without it.
    """

    def test_base_class_matches_the_backend_in_use(self):
        if get_tree_backend() == "mptree":
            from cms.utils.mptree import MaterializedPathMixin

            self.assertIs(TreeNodeBase, MaterializedPathMixin)
            self.assertTrue(BASE_MAINTAINS_PARENT)
        else:
            from treebeard.mp_tree import MP_Node

            self.assertIs(TreeNodeBase, MP_Node)
            self.assertFalse(BASE_MAINTAINS_PARENT)

    def test_node_is_built_on_the_selected_base(self):
        self.assertTrue(issubclass(ModerationRequestTreeNode, TreeNodeBase))


class TreeNodeParentTestCase(TestCase):
    """
    Whichever backend is in charge, ``parent`` has to describe the same tree as
    ``path`` -- the CMS core implementation reads the tree from the foreign key,
    treebeard from the path, and both must see a database written by the other.
    """

    def assertParentMatchesPath(self, node):
        node.refresh_from_db()
        if node.depth == 1:
            self.assertIsNone(node.parent_id)
        else:
            steplen = len(node.path) // node.depth
            self.assertEqual(node.parent.path, node.path[:-steplen])

    def test_root_node_has_no_parent(self):
        root = factories.RootModerationRequestTreeNodeFactory()

        self.assertIsNone(root.parent_id)
        self.assertParentMatchesPath(root)

    def test_added_child_points_at_its_parent(self):
        root = factories.RootModerationRequestTreeNodeFactory()

        child = factories.ChildModerationRequestTreeNodeFactory(parent=root)

        self.assertEqual(child.parent_id, root.pk)
        self.assertParentMatchesPath(child)
        self.assertEqual(list(root.children.all()), [child])

    def test_added_grandchild_points_at_its_parent(self):
        root = factories.RootModerationRequestTreeNodeFactory()
        child = factories.ChildModerationRequestTreeNodeFactory(parent=root)

        grandchild = factories.ChildModerationRequestTreeNodeFactory(parent=child)

        self.assertEqual(grandchild.parent_id, child.pk)
        self.assertParentMatchesPath(grandchild)

    def test_added_sibling_points_at_the_shared_parent(self):
        root = factories.RootModerationRequestTreeNodeFactory()
        child = factories.ChildModerationRequestTreeNodeFactory(parent=root)

        sibling = child.add_sibling(
            moderation_request=factories.ModerationRequestFactory()
        )

        self.assertEqual(sibling.parent_id, root.pk)
        self.assertParentMatchesPath(sibling)

    def test_moved_node_points_at_its_new_parent(self):
        root = factories.RootModerationRequestTreeNodeFactory()
        other_root = factories.RootModerationRequestTreeNodeFactory()
        child = factories.ChildModerationRequestTreeNodeFactory(parent=root)

        child.move(other_root, "last-child")

        self.assertParentMatchesPath(child)
        self.assertEqual(child.parent_id, other_root.pk)

    def test_collection_add_version_builds_the_parent_chain(self):
        collection = factories.ModerationCollectionFactory()
        parent_node = factories.RootModerationRequestTreeNodeFactory(
            moderation_request__collection=collection
        )

        collection.add_version(factories.PollVersionFactory(), parent_node)

        child = ModerationRequestTreeNode.objects.exclude(pk=parent_node.pk).get()
        self.assertEqual(child.parent_id, parent_node.pk)
        self.assertParentMatchesPath(child)

    def test_deleting_a_node_deletes_its_descendants(self):
        root = factories.RootModerationRequestTreeNodeFactory()
        child = factories.ChildModerationRequestTreeNodeFactory(parent=root)
        factories.ChildModerationRequestTreeNodeFactory(parent=child)

        root.delete()

        self.assertFalse(ModerationRequestTreeNode.objects.exists())

    def test_rebuild_parents_repairs_nodes_written_behind_the_tree_api(self):
        root = factories.RootModerationRequestTreeNodeFactory()
        child = factories.ChildModerationRequestTreeNodeFactory(parent=root)
        # As a raw ``create()`` or a treebeard ``load_bulk()`` would leave them
        ModerationRequestTreeNode.objects.filter(pk=child.pk).update(parent=None)

        ModerationRequestTreeNode.rebuild_parents()

        child.refresh_from_db()
        self.assertEqual(child.parent_id, root.pk)


class TreeChangelistTestCase(CMSTestCase):
    """
    The changelist renders the nesting itself, rather than leaving it to the
    client side tree of whichever tree library is installed.
    """

    def setUp(self):
        self.user = self.get_superuser()
        self.collection = factories.ModerationCollectionFactory(author=self.user)
        self.tree_admin = ModerationRequestTreeAdmin(
            ModerationRequestTreeNode, admin.AdminSite()
        )
        changelist_url = reverse(
            'admin:djangocms_moderation_moderationrequesttreenode_changelist'
        )
        self.url = (
            f"{changelist_url}?moderation_request__collection__id={self.collection.pk}"
        )

    def _node(self, parent=None):
        kwargs = {'moderation_request__collection': self.collection}
        if parent is None:
            return factories.RootModerationRequestTreeNodeFactory(**kwargs)
        return factories.ChildModerationRequestTreeNodeFactory(parent=parent, **kwargs)

    def test_root_row_is_not_indented(self):
        self.assertEqual(self.tree_admin.get_tree_indent(self._node()), '')

    def test_nested_rows_are_indented_by_their_depth(self):
        root = self._node()
        child = self._node(parent=root)
        grandchild = self._node(parent=child)

        self.assertIn('width: 2em', self.tree_admin.get_tree_indent(child))
        self.assertIn('width: 4em', self.tree_admin.get_tree_indent(grandchild))

    def test_changelist_lists_the_tree_depth_first(self):
        first_root = self._node()
        second_root = self._node()
        # Added last, so creation order alone would list it below ``second_root``
        # and the indentation would read as nesting under the wrong request.
        child = self._node(parent=first_root)

        with self.login_user_context(self.user):
            response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            [node.pk for node in response.context['cl'].result_list],
            [first_root.pk, child.pk, second_root.pk],
        )

    def test_changelist_renders_the_indentation(self):
        child = self._node(parent=self._node())

        with self.login_user_context(self.user):
            response = self.client.get(self.url)

        self.assertContains(response, 'cms-moderation-tree-indent')
        self.assertContains(response, f'>{child.moderation_request_id}</a>')


class TreeNodeApiTestCase(TestCase):
    """
    The bits of treebeard's node API the CMS core implementation does not
    provide, which the model fills in so a project's own changelist fields read
    the same under either backend.
    """

    def test_get_depth_reports_the_stored_depth(self):
        root = factories.RootModerationRequestTreeNodeFactory()
        child = factories.ChildModerationRequestTreeNodeFactory(parent=root)

        self.assertEqual(root.get_depth(), 1)
        self.assertEqual(child.get_depth(), 2)

    def test_get_children_count_reports_the_stored_numchild(self):
        root = factories.RootModerationRequestTreeNodeFactory()
        child = factories.ChildModerationRequestTreeNodeFactory(parent=root)

        root.refresh_from_db()
        self.assertEqual(root.get_children_count(), 1)
        self.assertEqual(child.get_children_count(), 0)


class TreeConsistencyTestCase(TestCase):
    """
    ``path`` and ``parent`` are two descriptions of one tree -- treebeard reads
    the first, the CMS core implementation the second -- so a database written
    by either backend has to describe the same nesting both ways.
    """

    def assertTreeIsConsistent(self):
        nodes = list(ModerationRequestTreeNode.objects.all())
        children_by_path = {node.pk: set() for node in nodes}
        children_by_parent = {node.pk: set() for node in nodes}
        pk_by_path = {node.path: node.pk for node in nodes}

        for node in nodes:
            if node.depth == 1:
                self.assertIsNone(
                    node.parent_id, f"root {node.pk} carries a parent"
                )
            else:
                steplen = len(node.path) // node.depth
                children_by_path[pk_by_path[node.path[:-steplen]]].add(node.pk)
            if node.parent_id is not None:
                children_by_parent[node.parent_id].add(node.pk)

        self.assertEqual(children_by_path, children_by_parent)
        for node in nodes:
            self.assertEqual(
                node.numchild,
                len(children_by_parent[node.pk]),
                f"numchild of {node.pk} does not match its children",
            )

    def _tree(self):
        root = factories.RootModerationRequestTreeNodeFactory()
        child = factories.ChildModerationRequestTreeNodeFactory(parent=root)
        factories.ChildModerationRequestTreeNodeFactory(parent=child)
        factories.ChildModerationRequestTreeNodeFactory(parent=root)
        return root, child

    def test_a_tree_built_through_the_node_api_reads_the_same_both_ways(self):
        self._tree()

        self.assertTreeIsConsistent()

    def test_a_tree_reshaped_through_the_node_api_reads_the_same_both_ways(self):
        _root, child = self._tree()
        other_root = factories.RootModerationRequestTreeNodeFactory()

        child.move(other_root, "last-child")

        self.assertTreeIsConsistent()

    def test_fix_tree_restores_consistency_after_a_stale_parent(self):
        _root, child = self._tree()
        # As a raw ``create()`` or a treebeard ``load_bulk()`` would leave it:
        # written without the tree API knowing, so one of the two descriptions
        # is now stale.
        ModerationRequestTreeNode.objects.filter(pk=child.pk).update(parent=None)

        ModerationRequestTreeNode.fix_tree()

        self.assertTreeIsConsistent()

    def test_fix_tree_re_derives_the_parent_under_treebeard(self):
        if BASE_MAINTAINS_PARENT:
            self.skipTest("the CMS core backend maintains ``parent`` itself")
        root, child = self._tree()
        ModerationRequestTreeNode.objects.filter(pk=child.pk).update(parent=None)

        ModerationRequestTreeNode.fix_tree()

        child.refresh_from_db()
        self.assertEqual(child.parent_id, root.pk)


class MigrationBackfillTestCase(TestCase):
    """
    Migration ``0021`` derives ``parent`` from the materialized path, the only
    description of the tree rows written before it have. Tests run with
    ``--nomigrations``, so the backfill is exercised as the function it is,
    against rows put into the state the migration would find them in.
    """

    def setUp(self):
        migration = import_module(
            "djangocms_moderation.migrations.0021_moderationrequesttreenode_parent"
        )
        self.populate_parent = migration.populate_parent
        self.schema_editor = SimpleNamespace(connection=connection)

    def _run(self):
        self.populate_parent(apps, self.schema_editor)

    def _forget_parents(self):
        """Put the rows back into the pre-migration state: ``path`` only."""
        ModerationRequestTreeNode.objects.update(parent=None)

    def test_backfills_the_parent_of_every_node(self):
        root = factories.RootModerationRequestTreeNodeFactory()
        child = factories.ChildModerationRequestTreeNodeFactory(parent=root)
        grandchild = factories.ChildModerationRequestTreeNodeFactory(parent=child)
        sibling = factories.ChildModerationRequestTreeNodeFactory(parent=root)
        self._forget_parents()

        self._run()

        for node, expected in (
            (root, None),
            (child, root.pk),
            (grandchild, child.pk),
            (sibling, root.pk),
        ):
            node.refresh_from_db()
            self.assertEqual(node.parent_id, expected)

    def test_leaves_roots_without_a_parent(self):
        root = factories.RootModerationRequestTreeNodeFactory()
        factories.RootModerationRequestTreeNodeFactory()
        self._forget_parents()

        self._run()

        self.assertEqual(
            list(
                ModerationRequestTreeNode.objects.filter(depth=1).values_list(
                    "parent", flat=True
                )
            ),
            [None, None],
        )
        root.refresh_from_db()
        self.assertIsNone(root.parent_id)

    def test_turns_a_node_with_a_missing_ancestor_into_a_root(self):
        root = factories.RootModerationRequestTreeNodeFactory()
        child = factories.ChildModerationRequestTreeNodeFactory(parent=root)
        self._forget_parents()
        # A tree left dangling by an earlier treebeard-unaware cascade delete.
        # Deleted behind the tree API, so no descendant is taken with it.
        with connection.cursor() as cursor:
            cursor.execute(
                f"DELETE FROM {ModerationRequestTreeNode._meta.db_table} WHERE id = %s",
                [root.pk],
            )

        self._run()

        child.refresh_from_db()
        self.assertIsNone(child.parent_id)

    def _raw_node(self, path, depth):
        """A row as some other tree writer would have left it: ``path`` only."""
        return ModerationRequestTreeNode.objects.create(
            moderation_request=factories.ModerationRequestFactory(),
            path=path,
            depth=depth,
        )

    def test_derives_the_parent_whatever_the_step_width(self):
        # Path segments are fixed width, one per level, but the width itself is
        # the tree's ``steplen`` -- which the backfill has to read off the row
        # rather than assume, or a project that widened it gets a broken tree.
        root = self._raw_node(path="00000A", depth=1)
        child = self._raw_node(path="00000A00000B", depth=2)
        grandchild = self._raw_node(path="00000A00000B00000C", depth=3)

        self._run()

        child.refresh_from_db()
        grandchild.refresh_from_db()
        self.assertEqual(child.parent_id, root.pk)
        self.assertEqual(grandchild.parent_id, child.pk)

    def test_is_idempotent(self):
        root = factories.RootModerationRequestTreeNodeFactory()
        child = factories.ChildModerationRequestTreeNodeFactory(parent=root)
        self._forget_parents()

        self._run()
        self._run()

        child.refresh_from_db()
        self.assertEqual(child.parent_id, root.pk)
