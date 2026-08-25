.. _settings:

Settings
========

All settings are optional and live in your Django settings file.

``CMS_MODERATION_DEFAULT_COMPLIANCE_NUMBER_BACKEND``
----------------------------------------------------

Default: ``"djangocms_moderation.backends.uuid4_backend"``

The compliance number backend preselected for new workflows. See
:ref:`compliance_numbers`.

``CMS_MODERATION_COMPLIANCE_NUMBER_BACKENDS``
---------------------------------------------

Default: the three built-in backends (``uuid4_backend``,
``sequential_number_backend``,
``sequential_number_with_identifier_prefix_backend``)

A tuple of ``(dotted_path, label)`` pairs defining the backends available
in the workflow admin. Add your own backend here — see
:ref:`compliance_numbers`.

``CMS_MODERATION_COLLECTION_COMMENTS_ENABLED``
----------------------------------------------

Default: ``True``

Whether comments can be added to a :term:`Moderation Collection`. Disabling
removes the comments link from the collection changelist.

``CMS_MODERATION_REQUEST_COMMENTS_ENABLED``
-------------------------------------------

Default: ``True``

Whether comments can be added to individual :term:`Moderation Requests
<Moderation Request>`. Disabling removes the comments link from the
moderation request changelist.

``CMS_MODERATION_COLLECTION_NAME_LENGTH_LIMIT``
-----------------------------------------------

Default: ``24``

Maximum number of characters of the collection name shown in toolbar button
labels (e.g. *In collection "…"*); longer names are truncated with an
ellipsis. Set to ``None`` to never truncate.

``EMAIL_NOTIFICATIONS_FAIL_SILENTLY``
-------------------------------------

Default: ``False``

When ``True``, errors while sending notification emails are suppressed
instead of raising an exception. See :ref:`customize_notifications`.

``CMS_MODERATION_DEFAULT_CONFIRMATION_PAGE_TEMPLATE``
-----------------------------------------------------

Default: ``"djangocms_moderation/moderation_confirmation.html"``

Default template for confirmation pages — a legacy feature, see
:ref:`internals`.

``CMS_MODERATION_CONFIRMATION_PAGE_TEMPLATES``
----------------------------------------------

Default: only the default template above

A tuple of ``(template_path, label)`` pairs available in the confirmation
page admin.

``CMS_MODERATION_ENABLE_UNPUBLISHING``
--------------------------------------

Default: ``False``

Opt-in flag for the moderated **unpublish** flow. When enabled, collection
authors can create *unpublish* collections: published content is added to a
collection and, once it has passed the *same* review workflow used for
publishing, it is unpublished instead of published. Enabling the flag also:

* adds a **Submit for unpublishing** link to published, moderated versions in
  the versioning admin, and
* removes the direct *unpublish* link from moderated content, so unpublishing
  always goes through moderation.

While disabled (the default), collections can only publish content and no
unpublish entry points are shown — behaviour is unchanged from before the
feature existed. Collections always default to publishing; unpublishing must be
chosen deliberately per collection.

``CMS_MODERATION_ENABLE_WORKFLOW_OVERRIDE``
-------------------------------------------

Default: ``False``

.. warning::

    This setting currently has **no effect**. It is a remnant of
    django CMS Moderation 1.x, where moderation was started per request
    rather than per collection, and is kept for backwards compatibility of
    settings files only.
