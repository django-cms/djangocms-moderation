Integrating Moderation
======================

.. toctree::
   :maxdepth: 2
   :caption: Contents:

Moderation depends on Versioning, so first install that. The content-type models that should be moderated need to be registered. This can be done in `cms_config.py` file:

.. code-block:: python

    # blog/cms_config.py
    from collections import OrderedDict
    from cms.app_base import CMSAppConfig
    from djangocms_versioning.datastructures import VersionableItem, default_copy
    from .models import PostContent

    def get_preview_url(obj):
        # generate url as required
        return obj.get_absolute_url()

    def stories_about_intelligent_cats(request, version, *args, **kwargs):
        return version.content.cat_stories


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

1. This must be set to True for Versioning to read app's CMS config.
2. This must be set to True for Moderation to read app's CMS config.
3. `versioning` attribute takes a list of `VersionableItem` objects. See `djangocms_versioning` documentation for details.
4. `moderated_models` attribute takes a list of moderatable model objects.