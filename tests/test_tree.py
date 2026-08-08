from django.contrib import admin
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
