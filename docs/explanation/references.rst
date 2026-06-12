.. _references:

Integration with djangocms-references
=====================================

Moderation integrates with the `djangocms-references
<https://github.com/fidelityinternational/djangocms-references>`_ package
when it is installed. On the confirmation screen of the publish action, all
content records that would be affected by publishing — for example pages
that include the content being published — are listed for a final check
before confirming.

No configuration is required; the integration activates automatically when
``djangocms_references`` is part of the project.
