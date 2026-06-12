.. _overview:

How moderation works
====================

Moderation provides an approval workflow for organisations that need
content to be signed off before it is published. It extends and complements
`djangocms-versioning
<https://github.com/django-cms/djangocms-versioning>`_, which it depends
on: moderation always operates on *draft versions* of content, and
publishing remains a versioning operation — moderation controls *when* and
*by whom* it may happen.

The big picture
---------------

A draft that is ready for sign-off is added to a :term:`Moderation
Collection` — a batch of content (think of a chapter, edition or release)
intended to be reviewed and published together. Any number of drafts, of
any registered content type, can be collected.

Each collection follows a :term:`Workflow`: an ordered list of approval
steps, each assigned to a :term:`Role` (a user or a group). When the
collection's author submits it for review, the drafts in it are locked
against editing and the reviewers of the first step are notified.

Inside the collection, every draft is wrapped in a :term:`Moderation
Request` — a "request to publish" that accumulates the review metadata:
approvals, rejections, comments, timestamps and (optionally) a compliance
number. Reviewers approve requests step by step, or send them back to the
author for rework. Once a request has passed every required step, the
collection's author can publish it; when all requests in a collection have
been moderated, the collection archives itself.

The lifecycle at a glance
-------------------------

.. code-block:: text

    author                          reviewers                 author
    ──────────────────────────────  ────────────────────────  ─────────────
    create collection
    add drafts ("Submit for
      moderation")
    submit collection for review →  approve ─────────────────→ publish
        (drafts become locked)  →  or reject ("rework")
                                        ↓
                                    author edits & resubmits
                                        ↻ (review starts over)

Which content is moderated?
---------------------------

Moderation uses the app registration features of django CMS 4+ to let each
application declare which of its versioned content types are moderated
(see :ref:`cms_config`). It is therefore possible to run a project where
pages require approval while other content types publish directly. Pages
themselves are registered by default.

Where moderation hooks into the CMS
-----------------------------------

* On draft versions of registered content types, versioning's **Publish**
  toolbar button is replaced with **Submit for moderation** — direct
  publishing is disabled for moderated models.
* The collection and its requests are managed in the Django admin, under
  **django CMS Moderation**.
* Notifications go out by email at each hand-over point (submission,
  approval, rejection, cancellation), and :ref:`signals` let your code
  react to moderation events.
