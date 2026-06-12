.. _lock:

Review locking
==============

As soon as a :term:`Moderation Collection` is submitted for review, its
content is protected from changes that would invalidate the review. Two
locks come into effect:

Collection lock
    No new drafts can be added to the collection. Drafts can only be added
    while the collection is in its *Collecting* state.

Version lock
    The draft versions in the collection can no longer be edited — by
    anyone, including the collection author. In the CMS toolbar the
    **Edit** button is disabled for review-locked content.

The locks are lifted again when:

* a reviewer **rejects** a request — the lock is lifted *for the author
  only*, so they can rework the content and resubmit it;
* a draft is **removed** from the collection;
* the collection is **cancelled**;
* the version is **published** — published versions are no longer drafts,
  and moderation of them is finished.

Third-party code can check the lock with
:py:func:`~djangocms_moderation.helpers.is_obj_review_locked` — see
:ref:`helpers`.
