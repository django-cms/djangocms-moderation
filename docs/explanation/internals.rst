.. _internals:

Internals
=========

Notes on the implementation, aimed at contributors and at developers
debugging an integration. Nothing here is part of the public Python API,
though the templates named below are meant to be overridden by projects.

How moderation modifies Versioning's UI
---------------------------------------

``monkeypatch.py``
    Moderation monkeypatches parts of djangocms-versioning's admin:
    ``get_state_actions`` gains a **Submit for moderation** icon button next
    to draft versions in the version table (see `Admin action icons`_), and
    additional checks are added to versioning's check framework to block
    operations (edit, revert, discard, …) at certain stages of moderation.

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

Admin action icons
------------------

Per-row actions in moderation's changelists follow django CMS's convention
and are rendered as icon buttons — an ``<a class="btn cms-action-btn">``
around a 20×20 glyph — rather than as text links. The wording of the action
is kept as the button's ``title``, which is both its tooltip and its
accessible name.

Each button is a small, overridable template. All paths below are relative
to ``djangocms_moderation/templates/djangocms_moderation/``:

============================  =========================================  =========================================
Tooltip                       Template                                   Shown in
============================  =========================================  =========================================
**Submit for moderation**     ``icons/submit_for_moderation.html``       versioning's version table, on moderated
                                                                         drafts
**Submit for unpublishing**   ``icons/submit_for_unpublishing.html``     versioning's version table, on moderated
                                                                         published versions — only while
                                                                         ``CMS_MODERATION_ENABLE_UNPUBLISHING``
                                                                         is on (see :ref:`unpublishing`)
**Edit Collection Settings**  ``edit_icon.html``                         collections changelist
**View Requests**             ``request_icon.html``                      collections changelist
**View Comments**             ``comment_icon.html``                      collections and requests changelists
============================  =========================================  =========================================

Where django CMS's own icon font offers a suitable glyph, the template uses
it directly (``<span class="cms-icon cms-icon-pencil">``). The two *submit*
actions have no counterpart in that font, so they embed `Bootstrap Icons
<https://icons.getbootstrap.com>`_ instead: ``send-check`` for submitting
content to be published, ``send-dash`` for submitting it to be unpublished.
Bootstrap Icons is MIT licensed; the notice is reproduced in ``LICENSE.txt``.

Those two icons are inlined in the template rather than shipped as static
``.svg`` files and referenced with ``<img>``. As inline markup the SVG
inherits ``fill="currentColor"`` from the button, so it follows django CMS's
light and dark admin themes; an image reference would resolve the colour in
the SVG's own context and stay black on a dark background.

Both extend ``djangocms_moderation/icons/base.html``, which renders the
anchor and leaves three blocks to fill in — ``name`` (appended to the CSS
class as ``cms-moderation-action-{name}``), ``title`` (the tooltip) and
``icon`` (the glyph). To swap in a different glyph, shadow the template in
your project and override just the ``icon`` block:

.. code-block:: html+django

    {# myproject/templates/djangocms_moderation/icons/submit_for_moderation.html #}
    {% extends "djangocms_moderation/icons/base.html" %}
    {% load i18n %}
    {% block title %}{% translate "Send to review" %}{% endblock %}
    {% block name %}submit-for-moderation{% endblock %}
    {% block icon %}<span class="cms-icon cms-icon-moderate"></span>{% endblock %}

The buttons are sized and coloured by django CMS's ``cms.admin.css``, which
the version table already loads through versioning's admin; moderation's own
changelists add ``djangocms_moderation/css/actions.css`` on top.

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
