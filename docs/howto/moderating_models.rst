.. _moderating_models:

How to moderate your own content types
======================================

Any versioned content model can be put under moderation. This guide
registers an imaginary ``PostContent`` model of a ``blog`` app.

Prerequisites: the model must be registered with djangocms-versioning —
moderation operates on its draft versions. See the
`djangocms-versioning documentation
<https://djangocms-versioning.readthedocs.io>`_ for how to do that.

Register the model
------------------

In your app's ``cms_config.py``, enable moderation and list the content
models to moderate:

.. code-block:: python

    # blog/cms_config.py
    from cms.app_base import CMSAppConfig
    from djangocms_versioning.datastructures import VersionableItem, default_copy

    from .models import PostContent


    class BlogCMSConfig(CMSAppConfig):
        djangocms_versioning_enabled = True
        djangocms_moderation_enabled = True
        versioning = [
            VersionableItem(
                content_model=PostContent,
                grouper_field_name="post",
                copy_function=default_copy,
            ),
        ]
        moderated_models = [PostContent]

That is all that is required. Restarting the server gives you:

* a **Submit for moderation** toolbar button on draft ``PostContent``
  objects (for content types with a preview endpoint),
* an **Add to moderation collection** bulk action in the model's admin
  changelist,
* review locking for drafts that are part of a collection under review.

Mixing moderated and unmoderated models
---------------------------------------

``moderated_models`` does not have to mirror ``versioning``: you can
version a model without moderating it by leaving it out of
``moderated_models``. This lets you configure your project so that, for
example, pages require approval while news items publish directly.

Customise the moderation request changelist
-------------------------------------------

Apps can contribute extra columns and extra entries to the action menu of
the moderation requests changelist (the view reviewers work in):

.. code-block:: python

    # blog/cms_config.py
    from django.utils.html import format_html


    def language_column(node):
        return node.moderation_request.language
    language_column.short_description = "Language"


    def dashboard_link(node):
        return format_html(
            '<a href="/dashboard/{}/">Open in dashboard</a>',
            node.moderation_request.pk,
        )


    class BlogCMSConfig(CMSAppConfig):
        # ... as above, plus:
        moderation_request_changelist_fields = [language_column]
        moderation_request_changelist_actions = [dashboard_link]

Each entry is a callable receiving the changelist row object (a
``ModerationRequestTreeNode``); the underlying
:class:`~djangocms_moderation.models.ModerationRequest` is available as its
``moderation_request`` attribute. ``moderation_request_changelist_fields``
callables are added as list-display columns (set ``short_description`` for
the column header); ``moderation_request_changelist_actions`` callables
should return HTML that is appended to the **Actions** column.

See :ref:`cms_config` for the full reference of configuration attributes.
