Integrating Moderation
======================

.. toctree::
   :maxdepth: 2
   :caption: Contents:

Moderation depends on `Versioning <https://github.com/divio/djangocms-versioning>`_ to be installed. The content-type models that should be moderated need to be registered. This can be done in `cms_config.py` file:

.. code-block:: python

    # blog/cms_config.py
    from collections import OrderedDict
    from cms.app_base import CMSAppConfig
    from djangocms_versioning.datastructures import VersionableItem, default_copy
    from .models import PostContent

    def get_preview_url(obj):
        # generate url as required
        return obj.get_absolute_url()

    def get_blog_additional_changelist_action(obj):
        return "Custom moderation action"

    def get_blog_additional_changelist_field(obj):
        return "Custom moderation field"
    get_poll_additional_changelist_field.short_description = "Custom Field"

    class BlogCMSConfig(CMSAppConfig):
        djangocms_versioning_enabled = True  # -- 1
        djangocms_moderation_enabled = True  # -- 2
        versioning = [
            VersionableItem(   # -- 3
                content_model=PostContent,
                grouper_field_name='post',
                copy_function=default_copy,
                preview_url=get_preview_url,
            ),
        ]
        moderated_models = [   # -- 4
          PostContent,
        ]
        moderation_request_changelist_actions = [   # -- 5
            get_blog_additional_changelist_action
        ]
        moderation_request_changelist_fields = [   # -- 6
            get_blog_additional_changelist_field
        ]


1. This must be set to True for Versioning to read app's CMS config.
2. This must be set to True for Moderation to read app's CMS config.
3. `versioning` attribute takes a list of `VersionableItem` objects. See `djangocms_versioning` documentation for details.
4. `moderated_models` attribute takes a list of moderatable model objects.
5. `moderation_request_changelist_actions` attribute takes a list of actions that are added to the action field in the Moderation Request Changelist admin view
6. `moderation_request_changelist_fields` attribute takes a list of admin fields that are added to the display list in the Moderation Request Changelist admin view
