.. _role:

Role
================================================
Understanding the Role model can be a bit tricky because it blurs the lines between the CMS permissions system and the custom permission system implemented by Moderation. So let's break this down a bit...

Firstly from a CMS permissions perspective - you can define whatever Groups you like to the various standard and customer model permissions for Moderation (e.g. `add_moderationcollection`). However, the recommendation is the following groups: Editor, Publisher and Reviewer. The Reviewer should have permission to view the :ref:`moderation_collection` only (and should generally have very limited access to the CMS - no edit / create permissions for content-types in general. The Editor should have rights to view and edit a :ref:`moderation_collection`. The Publisher should have rights to create, edit, cancel and view a :ref:`moderation_collection`.

For the purpose of this explanation - `Role` (capitalised) and `role` (lowercase) - `Role` refers to the model, whereas `role` refers to the word "role" in the normal broad application of the English term.

Moderation has internal permissions logic which does not involve CMS permissions but rather which defines two `roles`, each which will have differing access to parts of the Moderation UI/UX. These `roles` are `Collection author` and `Reviewer`.

`Collection author` is defined simply by the `author` fk link to a user on the ModerationCollection model instance. It is always a single User. For this user, the following bulk actions will be enabled in the Moderation's change_list view , namely `cancel collection`, `publish` and `remove`.

`Reviewer` is a more nebulous concept. A ModerationCollection may have a number of `Reviewers`. The :ref:`workflow` has one or more :ref:`workflow_step` each which have a single Role assigned to it. The Role links to either a single User or a Group of Users. This dynamically determines a set of users that are valid `Reviewers` for a given :ref:`moderation_request` at a given :ref:`workflow_step`. Once a valid `Reviewer` acts on a given :ref:`moderation_request`, their action is recorded as a :ref:`moderation_request_action`. A `Reviewer` has access to a compliment of bulk actions - specifically allowing a `Reviewer` to `accept` or `reject` a draft version.

A User may be both a `Reviewer` and a `Collection author` for a given :ref:`moderation_collection`.

Thus, the Role model defines `the person/s who is responsible for reviewing a particular step of the workflow`. I.e. it defines the users that may review a `draft` version for a given :ref:`moderation_request` for a given Collection.

In summary...

Reviewer
------------------------------------------------
The Reviewer is responsible for approving / rejecting items in the collection and making comments.
They have access to the `Approve` and `Submit for rework` :ref:`moderation_collection` bulk actions.

Collection author
------------------------------------------------
The collection author is responsible for creating, editing and (usually) publishing the collection. They have access to the `Submit for review` and `Publish` :ref:`moderation_collection` bulk actions, as well as the various :ref:`moderation_collection` buttons.
