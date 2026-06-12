.. _customize_notifications:

How to customise email notifications
====================================

Moderation sends two kinds of email out of the box:

* **To the reviewers** of the current workflow step — when a collection is
  submitted for review or a rejected request is resubmitted.
* **To the collection author** — when reviewers approve or reject content,
  and when a collection is cancelled.

Emails are sent with Django's standard email machinery, from
``DEFAULT_FROM_EMAIL``, so your project needs a working
`email configuration <https://docs.djangoproject.com/en/stable/topics/email/>`_.

Override the email templates
----------------------------

The notification bodies are plain-text Django templates. Override them by
placing files with the same path in your project's ``templates`` directory:

.. code-block:: text

    templates/
        djangocms_moderation/
            emails/
                moderation-request/
                    request.txt    # to reviewers: action required
                    approved.txt   # to the author: content was approved
                    rejected.txt   # to the author: content needs rework
                    cancelled.txt  # to the author: collection was cancelled

The template context provides:

``collection``
    The :class:`~djangocms_moderation.models.ModerationCollection` concerned.

``moderation_requests``
    The list of :class:`~djangocms_moderation.models.ModerationRequest`
    objects the notification is about.

``author_name``
    The collection author's full name.

``by_user``
    The user whose action triggered the notification.

``admin_url``
    Absolute URL of the collection's moderation request list, for a
    "review now" style link.

``job_id``
    The collection's job id, as shown in the admin.

Let email failures pass silently
--------------------------------

By default a failing mail server raises an exception and aborts the user's
action. If notifications are not critical in your setup, let them fail
silently::

    EMAIL_NOTIFICATIONS_FAIL_SILENTLY = True

Send notifications through another channel
------------------------------------------

To notify a chat system or ticketing tool instead of (or in addition to)
email, connect to the :ref:`moderation signals <signals>` —
``submitted_for_review`` and ``published`` carry the collection, the
affected requests and the acting user.
