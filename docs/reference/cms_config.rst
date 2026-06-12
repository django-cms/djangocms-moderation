.. _cms_config:

App configuration (``cms_config.py``)
=====================================

Apps integrate with moderation through django CMS's app registration
system: a ``cms_config.py`` module containing a
:class:`cms.app_base.CMSAppConfig` subclass. See :ref:`moderating_models`
for a worked example.

Attributes read by moderation
-----------------------------

``djangocms_moderation_enabled``
    Must be ``True`` for moderation to read the app's configuration.

``moderated_models``
    A list of versioned content models to put under moderation. Every model
    listed here must also be registered with djangocms-versioning (in the
    same or another app's ``versioning`` attribute), and
    ``djangocms_versioning_enabled`` must be ``True`` — otherwise an
    ``ImproperlyConfigured`` error is raised at startup.

``moderation_request_changelist_fields``
    Optional. A list of callables added as columns to the moderation
    request changelist. Each callable receives the changelist row object
    (a ``ModerationRequestTreeNode``) and may set ``short_description``
    for the column header.

``moderation_request_changelist_actions``
    Optional. A list of callables whose returned HTML is appended to the
    **Actions** column of the moderation request changelist. Each callable
    receives the changelist row object.

What registration does
----------------------

For every model in ``moderated_models``:

* draft versions get a **Submit for moderation** button in the CMS toolbar
  (for preview-enabled content types) instead of versioning's direct
  **Publish** button;
* an **Add to moderation collection** bulk action is added to the model's
  admin changelist, if the model is registered with the admin;
* drafts belonging to a collection that is in review are review-locked
  (see :ref:`lock`).

Default configuration
---------------------

Moderation ships its own ``cms_config.py`` that registers django CMS pages
(``cms.models.PageContent``) for moderation. Installing the app therefore
moderates pages without any further configuration.

.. note::

    There is currently no setting to opt pages out of moderation while the
    app is installed.
