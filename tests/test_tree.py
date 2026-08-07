from django.test import TestCase

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
