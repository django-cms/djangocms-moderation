.. _signals:

Signals
=======


.. module:: djangocms_moderation.signals
   :synopsis: Signals sent by the moderation.

The :mod:`djangocms_moderation.signals` module defines a set of signals sent by
Django CMS Moderation.

``submitted_for_review``
------------------------

.. attribute:: djangocms_moderation.submitted_for_review
   :module:

.. ^^^^^^^ this :module: hack keeps Sphinx from prepending the module.

Sent when a :ref:`moderation_collection` is submitted for review,
or when select :ref:`Moderation Requests <moderation_request>`
are resubmitted after being rejected.

Arguments sent with this signal:

``sender``
    :class:`djangocms_moderation.models.ModerationCollection` class

``collection``
    A :class:`djangocms_moderation.models.ModerationCollection` instance
    which was submitted for review

``moderation_requests``
    A list of :class:`djangocms_moderation.models.ModerationRequest` instances
    which were submitted for review

    .. note::

        It's possible for this list to contain only some of the requests
        belonging to the collection being moderated,
        because only some of the requests required rework.

        This case is only possible for resubmitting after a rework.

``user``
    A :class:`django.contrib.auth.models.User` instance which triggered
    the submission

``rework``
    A :class:`bool` value specifying if this was the first time the
    collection was submitted, or a rework of its moderation requests
