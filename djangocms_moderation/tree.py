"""
Backend selection for the moderation request tree.

django CMS 5.0.10 and 5.1.1 ship ``cms.utils.mptree``, a dependency free
re-implementation of the ``django-treebeard`` ``MP_Node`` API the page tree
uses. Projects pick the implementation with the ``CMS_TREE_BACKEND`` setting
(``"treebeard"``, the default, or ``"mptree"``). Both declare the same columns,
so switching is a restart, not a migration.

``ModerationRequestTreeNode`` follows that setting, so a project running the CMS
page tree on ``mptree`` does not pull ``django-treebeard`` back in through the
moderation tree.

The one structural difference between the two: the CMS core implementation
treats a self referential ``parent`` foreign key as the source of truth and
maintains it, whereas treebeard derives the tree from ``path`` alone and leaves
``parent`` untouched. ``ModerationRequestTreeNode`` therefore declares the field
in both cases and keeps it in step itself when treebeard is in charge -- that
way the same database is readable by either backend.
"""

try:
    from cms.utils.mptree import MaterializedPathMixin, get_tree_backend, get_tree_base
except ImportError:  # django CMS < 5.0.10 / < 5.1.1: treebeard is the only option
    MaterializedPathMixin = None

    def get_tree_backend():
        """The name of the tree implementation in use."""
        return "treebeard"

    def get_tree_base():
        """The base class for materialized path models."""
        from treebeard.mp_tree import MP_Node

        return MP_Node


#: Base class for ``ModerationRequestTreeNode``, resolved once at import time --
#: as the CMS core does for ``Page`` -- so a backend change takes a restart.
TreeNodeBase = get_tree_base()

#: Whether the base class maintains the ``parent`` foreign key by itself. Derived
#: from the resolved base rather than from the setting, so the two cannot drift
#: apart if the setting is changed after import (e.g. by ``override_settings``).
BASE_MAINTAINS_PARENT = MaterializedPathMixin is not None and issubclass(
    TreeNodeBase, MaterializedPathMixin
)


__all__ = [
    "BASE_MAINTAINS_PARENT",
    "TreeNodeBase",
    "get_tree_backend",
    "get_tree_base",
]
