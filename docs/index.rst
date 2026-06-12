django CMS Moderation
=====================

django CMS Moderation adds editorial approval workflows to django CMS:
draft content is gathered into collections, routed through configurable
review steps, and published only once the right people have signed it off.
It builds on `djangocms-versioning
<https://github.com/django-cms/djangocms-versioning>`_.

New to moderation? Start with the hands-on :ref:`tutorial` — it takes you
from an empty project to publishing a page through a review workflow in
about 30 minutes.

.. toctree::
   :maxdepth: 2
   :caption: Tutorial

   tutorial/index

.. toctree::
   :maxdepth: 2
   :caption: How-to guides

   howto/index

.. toctree::
   :maxdepth: 2
   :caption: Reference

   reference/index

.. toctree::
   :maxdepth: 2
   :caption: Explanation

   explanation/index


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
