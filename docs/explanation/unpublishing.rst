.. _unpublishing:

Unpublishing moderated content
==============================

Moderation is built around *publishing*: drafts are gathered into a
:term:`Moderation Collection`, reviewed, and published once they have passed
the :term:`Workflow`. Taking already-published content back offline —
*unpublishing* — can happen in one of two ways, depending on a single
setting.

By default, unpublishing is a plain versioning operation that is **not**
moderated. Setting ``CMS_MODERATION_ENABLE_UNPUBLISHING = True`` routes it
through the *same* review workflow used for publishing.

Regular unpublishing (the default)
----------------------------------

With ``CMS_MODERATION_ENABLE_UNPUBLISHING`` unset or ``False``, moderation
only governs publishing. Unpublishing remains a direct
`djangocms-versioning <https://github.com/django-cms/djangocms-versioning>`_
action: whoever has permission to unpublish a version sees the **Unpublish**
link in the versioning admin and can take the content offline immediately,
without any review.

This matches the behaviour from before the feature existed. It is a sensible
default: blocking the direct link without offering an alternative would leave
moderated content with no way to be unpublished at all.

Moderated unpublishing (the workflow)
-------------------------------------

When ``CMS_MODERATION_ENABLE_UNPUBLISHING = True``, unpublishing becomes a
reviewed operation that mirrors publishing exactly. The review
:term:`Workflow` is identical — the same steps, roles and approvals apply;
only the eligible content and the final outcome differ:

================  ============================  ==============================
                  Publish collection            Unpublish collection
================  ============================  ==============================
Content added     draft versions                published versions
Review            workflow steps / approvals    *identical*
On completion     content is **published**      content is **unpublished**
================  ============================  ==============================

A collection carries this intent in its **action** field, chosen when it is
created. Collections always default to *publish*; *unpublish* must be selected
deliberately, so the two kinds never mix.

The lifecycle is the same as for publishing (see :ref:`overview`):

#. The author adds published content to an *unpublish* collection. In the
   versioning admin, published moderated versions gain a **Submit for
   unpublishing** link (the counterpart of **Submit for moderation** on
   drafts).
#. The author submits the collection for review; reviewers approve or send it
   back for rework, step by step.
#. Once every required step has approved, the author finalises the collection
   and the content is unpublished. An ``unpublished`` signal is sent so your
   code can react (see :ref:`signals`).

While the feature is enabled, the **direct** unpublish link is removed from
moderated content, so unpublishing always goes through moderation rather than
bypassing it (this closes the gap described in issue #165). The direct link is
only suppressed when the moderated alternative exists — turning the feature off
restores it.

In-flight collections
---------------------

The setting gates *starting* unpublish work, not finishing it. An unpublish
collection created while the feature was enabled can still be reviewed and
finalised even if the setting is later turned off, so reviews already under
way are never stranded.

See :ref:`settings` for the setting and :ref:`workflow` for how the shared
review workflow is configured.
