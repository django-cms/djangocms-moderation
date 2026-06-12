.. _moderation_collection:

Moderation Collections
======================

A Moderation Collection groups draft content versions together for review
and publishing. Grouping is the unit of work in moderation: reviewers are
invited per collection, locking applies per collection, and publishing
happens from within a collection.

Each collection has an **author** (also called its *moderator*) — the user
who created it — and a :term:`Workflow` that defines its approval steps.
The workflow can only be changed while the collection is still collecting
content.

States
------

A collection moves through four states:

Collecting
    The initial state. The author — and only the author — can add draft
    versions to the collection. Content is added from the CMS toolbar of a
    draft (**Submit for moderation**) or via the **Add to moderation
    collection** bulk action in a registered model's admin changelist.

In review
    Entered when the author clicks **Submit collection for review**. The
    reviewers of the first workflow step are notified, and the drafts in
    the collection become :ref:`review-locked <lock>`: they cannot be
    edited, and no further drafts can be added. Reviewers now act on the
    collection's :term:`Moderation Requests <Moderation Request>`.

Archived
    A finished collection. A collection archives itself automatically as
    soon as every remaining request in it has been approved and acted upon
    (published or removed). Archived collections cannot be modified; the
    state exists mainly to keep the collection list tidy and filterable.

Cancelled
    A collection can be cancelled by its author at (almost) any stage,
    provided they hold the *Can cancel collection* permission. Cancelling
    deactivates all active moderation requests, releases the locks and
    notifies the author of each affected draft.

Working with a collection in review
-----------------------------------

The collection's requests changelist offers bulk actions. Which of them a
given user sees depends on their relationship to the collection — see
:ref:`role`:

Approve
    (Reviewers) Approve the selected requests for the current workflow
    step. If a later step exists, its reviewers are notified; otherwise the
    request becomes ready for publishing.

Submit for rework
    (Reviewers) Reject the selected requests. The author is notified and
    the review lock is lifted *for the author only*, so they can edit the
    content. Previous approvals are archived — after resubmission the
    workflow starts again from the first step.

Submit for review
    (Author) Resubmit reworked requests, notifying the reviewers again.

Publish
    (Author) Publish the selected approved requests. This triggers
    versioning's publish operation and ends moderation for those drafts.

Remove from collection
    (Author) Take a draft out of the collection, releasing its lock.
