django CMS Moderation
=====================

django CMS Moderation adds editorial approval workflows to django CMS:
draft content is gathered into collections, routed through configurable
review steps, and published only once the right people have signed it off.
It builds on `djangocms-versioning
<https://github.com/django-cms/djangocms-versioning>`_.

New to moderation? Start with the hands-on :ref:`tutorial <tutorial>` — its
quick-start takes you from an empty project to a published page in about ten
minutes, and a second part adds a full review workflow with a separate
reviewer.

.. toctree::
   :maxdepth: 1
   :caption: Tutorial

   tutorial/quickstart
   tutorial/review_process

.. toctree::
   :maxdepth: 1
   :caption: How-to guides

   howto/installation
   howto/moderating_models
   howto/notifications
   howto/compliance_numbers
   howto/repair_states

.. toctree::
   :maxdepth: 1
   :caption: Reference

   reference/settings
   reference/cms_config
   reference/signals
   reference/management_commands
   reference/helpers

.. toctree::
   :maxdepth: 1
   :caption: Explanation

   explanation/how_it_works
   explanation/collections
   explanation/requests
   explanation/workflows
   explanation/roles
   explanation/lock
   explanation/comments
   explanation/references
   explanation/internals


Glossary
--------

.. glossary::

   Moderation
      A process by which a draft version (see
      `djangocms-versioning <https://github.com/django-cms/djangocms-versioning>`_)
      goes through an approval process before it can be published.

   Moderation Collection
      A collection (or batch) of drafts that is reviewed and published
      together. See :ref:`moderation_collection`.

   Moderation Request
      Each draft in a :term:`Moderation Collection` is wrapped in a
      Moderation Request — a "request to publish" carrying the review
      metadata such as approvals and comments. See :ref:`moderation_request`.

   Moderation Request Action
      A recorded event in the life of a :term:`Moderation Request` — e.g.
      *approved*, *rejected*, *resubmitted* — including who acted and at
      which workflow step. See :ref:`moderation_request_action`.

   Workflow
      The approval process assigned to a :term:`Moderation Collection`: an
      ordered series of review steps. See :ref:`workflow`.

   WorkflowStep
      One step of a :term:`Workflow`, reviewed by a :term:`Role`. See
      :ref:`workflow_step`.

   Role
      Defines who reviews a given workflow step: a single user or a group.
      See :ref:`role`.


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
