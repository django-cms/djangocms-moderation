.. _role:

Roles and permissions
=====================

Moderation involves two permission systems that are easy to conflate: the
standard Django/CMS model permissions, and moderation's own internal logic
built around the **Role** model. This page untangles them.

The Role model
--------------

A Role answers one question: *who is responsible for reviewing a particular
workflow step?* It points at either a single user or a group (never both),
and is assigned to one or more :term:`Workflow Steps <WorkflowStep>`. For a
given :term:`Moderation Request` at a given step, the role determines the
set of users whose approval counts.

Internal roles: author and reviewers
------------------------------------

Independently of Django permissions, moderation distinguishes two parties
per collection and adjusts the admin UI accordingly:

Collection author
    The user who created the collection (its ``author`` field — labelled
    *moderator* in the admin). Always a single user. The author creates and
    edits the collection, adds content, submits it for review, resubmits
    reworked content, publishes approved content, and may cancel the
    collection. The bulk actions *Submit for review*, *Publish*, *Remove
    from collection* and the cancel button are reserved for the author.

Reviewers
    The users designated by the role of the workflow step a request is
    currently at — a dynamic set, since each step may name a different user
    or group. Reviewers see the *Approve* and *Submit for rework* bulk
    actions. Their decisions are recorded as :ref:`Moderation Request
    Actions <moderation_request_action>`.

The same user can be both author and reviewer of a collection.

Django permissions
------------------

The internal logic above controls *which moderation actions* a user may
take; ordinary Django model permissions still control *which admin pages*
they can open. A typical setup defines three groups:

* **Editor** — may view and edit moderation collections; creates content
  and submits it for moderation.
* **Publisher** — may create, edit, view and cancel collections. Cancelling
  additionally requires moderation's custom *Can cancel collection*
  permission.
* **Reviewer** — needs only view access to moderation collections and
  requests (and generally little else in the CMS).

There is also a custom *Can change collection author* permission gating the
ability to reassign a collection to a different author.
