from django import template

from treebeard.templatetags import admin_tree


register = template.Library()

# django-treebeard 4.8 rewrote its admin tree integration. The ``result_tree``
# tag signature changed from ``(context, cl, request)`` to ``(cl)`` and a new
# ``tree_context`` tag (consumed by client-side JS) replaced the server-rendered
# tree. ``tree_context`` therefore only exists on 4.8+ and is a reliable feature
# flag to pick the matching changelist partial.
TREEBEARD_NEW_ADMIN_TREE = hasattr(admin_tree, "tree_context")


@register.simple_tag
def treebeard_new_admin_tree():
    return TREEBEARD_NEW_ADMIN_TREE
