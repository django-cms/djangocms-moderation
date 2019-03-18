.. _role:

Role
================================================
There are two main roles (as defined in the CMS) in the Moderation process. Collection author and Reviewer. Each role may link to either a single User or to a Group. Moderation Roles are not Django permission-based. Because these two roles have different functions, their UX / UI for handling collections will differ. If you have both roles then you can have both sets of permissions. 

Each :ref:`moderation_request_action` must be assigned to a Role. This allows the moderation system to know the set of valid reviewers for a particular :ref:`moderation_request_action`.


Reviewer
------------------------------------------------
The Reviewer is responsible for approving / rejecting items in the collection and making comments.
They have access to the `Approve` and `Submit for rework` :ref:`moderation_collection` bulk actions.

Collection author
------------------------------------------------
The collection author is responsible for creating, editing and (usually) publishing the collection. They have access to the `Submit for review` and `Publish` :ref:`moderation_collection` bulk actions, as well as the various :ref:`moderation_collection` buttons.