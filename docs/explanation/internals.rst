.. _internals:

Internals
=========

Notes on the implementation, aimed at contributors and at developers
debugging an integration. Nothing here is part of the public API.

How moderation modifies Versioning's UI
---------------------------------------

``monkeypatch.py``
    Moderation monkeypatches parts of djangocms-versioning's admin:
    ``get_state_actions`` gains a **Submit for moderation** link next to
    draft versions in the version table, and additional checks are added to
    versioning's check framework to block operations (edit, revert,
    discard, …) at certain stages of moderation.

``cms_toolbars.py``
    Replaces versioning's toolbar with ``ModerationToolbar``, which swaps
    the **Publish** button for **Submit for moderation** / **In collection
    "…"** buttons and disables **Edit** for review-locked content.

``admin.py``
    Besides the model admins, this module generates the bulk-action
    confirmation views (``approve``, ``rework``, ``publish``, ``resubmit``,
    ``delete_selected``). The available bulk actions are filtered per user
    by moderation's internal role logic (see :ref:`role`), so different
    users see different action menus on the same changelist.

.. _tree_admin:

The tree changelist
-------------------

When a page is added to a collection, moderated draft content used by
plugins on that page (for example aliased content) is added along with it.
Presenting those additions as a flat list would hide why they are in the
collection, so the requests changelist is rendered as a tree
(django-treebeard's materialised path trees, via the
``ModerationRequestTreeNode`` model): nested entries belong to the page
they were collected with.

A consequence of modelling the *relationship* rather than the request is
that the same content object may appear several times in the tree — once
per page that pulled it in, plus once if it was added individually. It is
still only one moderation request: acting on any occurrence acts on all of
them, and removing it from the collection removes every occurrence.

.. image:: /_static/nested-layout.jpg

Confirmation pages (legacy)
---------------------------

The models :class:`~djangocms_moderation.models.ConfirmationPage` and
``ConfirmationFormSubmission`` (admin sections **Confirmation Pages** and
**Confirmation Form Submissions**) belong to a django CMS Moderation 1.x
feature where a reviewer could be required to fill in a form before
approving a step. The view rendering these pages still exists, but the
current bulk-action approval flow does not enforce or link to them — the
feature is effectively dormant and kept for data compatibility.
