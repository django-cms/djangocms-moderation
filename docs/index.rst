.. djangocms_moderation documentation master file, created by
   sphinx-quickstart on Fri Mar  1 11:52:55 2019.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to djangocms-moderation's documentation!
================================================

.. toctree::
   :maxdepth: 2
   :caption: User Documentation:

   overview
   moderation_collection
   comment
   lock
   moderation_request
   moderation_request_action
   role
   references
   workflow
   workflow_step


.. toctree::
   :maxdepth: 2
   :caption: Developer Documentation:

   introduction
   internals


Glossary
--------

.. glossary::

   Moderation
      A process by which a draft version (see docs for `djangocms-versioning <https://github.com/divio/djangocms-versioning>`_) goes through an approval process before it can be published.

   Moderation Collection
      A collection (or batch) of drafts ready for moderation.

   Moderation Request
      Each draft in a :ref:`moderation_collection` is wrapped as a :ref:`moderation_request` in order to associate additional :ref:`Workflow` -related data with that draft. Each request may also have comments added to it and may send out notifications

   Workflow
      Each :ref:`moderation_collection` is associated with a :ref:`workflow`. The workflow determines through what steps the moderation process needs to go and may provide a differing moderation UX for each Workflow.

   WorkflowStep
      Each :ref:`workflow` has at least one :ref:`workflow_step`.

   Moderation Request Action
      Each :ref:`moderation_request` will have a number of actions associated with it. The number of these is defined as part of the :ref:`workflow`. A :ref:`moderation_request_action` is the action taken by an actor who is part of the moderation process. E.g. "mark as approved", "request rework", "publish".

   Role
      Each :ref:`moderation_request_action` step in a :ref:`workflow` is associated with a Role. The Role consists either of a single User or a single Group. The users associated with that Role are required to act at that stage of the :ref:`workflow`.


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
