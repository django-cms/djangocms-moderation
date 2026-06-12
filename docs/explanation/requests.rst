.. _moderation_request:

Moderation Requests and Actions
===============================

While a :term:`Moderation Collection` groups drafts, the work of reviewing
happens on **Moderation Requests**. When a draft version is added to a
collection it is wrapped in a Moderation Request — conceptually, a *request
to publish* that draft. The request carries the metadata of the review:
who approved what and when, comments, rejection feedback and (optionally) a
compliance number.

Moderation Requests should not be confused with Django's HTTP request
objects — the two are unrelated.

.. _moderation_request_action:

Actions
-------

A Moderation Request does not store a state field. Instead it records every
event as a **Moderation Request Action** — *started*, *approved*,
*rejected*, *resubmitted*, *cancelled*, *finished* — along with the acting
user and, for approvals, the workflow step that was approved. The request's
state is *inferred* from this action log and from the state of the
underlying version. This gives a complete, auditable history of the review.

When a reviewer rejects a request, all its previous actions are archived:
after the author resubmits, every required step must approve again from the
beginning.

Inferred states
---------------

The admin derives and displays the following statuses:

Ready for submission
    No actions yet — the collection has not been submitted for review.

Pending *<role>* approval
    Waiting for the reviewers of the named workflow step to approve or
    reject.

Pending author rework
    The most recent action is a rejection: the author is expected to edit
    the content and resubmit it for review.

Ready for publishing
    Every required workflow step has approved, and the underlying version
    is still a publishable draft. The collection author can now publish.

Published
    The underlying version has been published; moderation of this request
    is finished.

Compliance numbers
------------------

If the collection's workflow requires it, the request receives a unique
compliance number at the moment it receives its final required approval —
see :ref:`compliance_numbers`.
