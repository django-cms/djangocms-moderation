.. _moderation_request:

Moderation Request
================================================
While the aim of a :ref:`collection` is to group draft Version objects together. This is achieved via an intermediary model :ref:`moderation_request` which allows meta-data such as approvals, comments, dates and actors to be associated with each draft as it goes through moderation.

Conceptually this entity can be thought of as a "request to publish" for a particular draft version. Thus the request tracks the meta-data associated with the moderation process for a particular draft.

Moderation Requests should not be confused with the standard Django request entity.

States
------------------------------------------------
Moderation Requests are not in and of themselves stateful however they contain one or more instances of the :ref:`moderation_request_action` entity, which is stateful and the Moderation Request state can be inferred from its `moderation request actions`. They also link to a draft version, which also has states. The inferred states for a request are:

Ready for review
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Waiting for approval / rejection. I.e. (@TODO: ???)

Ready for rework
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Waiting for editing and resubmission for review. I.e. contains one or more actions of the `rejected` state.

Approved
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Ready to be published. I.e. contains only actions of the 'approved' state.

Published
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
I.e. refers to a Published version - no longer a draft.