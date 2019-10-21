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



``published``
------------------------

.. attribute:: djangocms_moderation.published
   :module:

.. ^^^^^^^ this :module: hack keeps Sphinx from prepending the module.

Sent when a :ref:`moderation_collection` is being published

Arguments sent with this signal:

``sender``
    :class:`djangocms_moderation.models.ModerationCollection` class

``collection``
    A :class:`djangocms_moderation.models.ModerationCollection` instance
    which was submitted to be published.

``moderator``
    A :class:`django.contrib.auth.models.User` associated with the collection which is the moderator of the collection.

``moderation_requests``
    A list of :class:`djangocms_moderation.models.ModerationRequest` instances
    which were published.

    .. note::

        It's possible for this list to contain only some of the requests
        belonging to the collection being moderated,
        because only some of the requests were published.

``workflow``
    An instance of :class:`djangocms_moderation.models.Workflow` which was used for this collection.


``unpublished``
------------------------

.. attribute:: djangocms_moderation.unpublished
   :module:

.. ^^^^^^^ this :module: hack keeps Sphinx from prepending the module.

Sent when a :ref:`moderation_collection` is being unpublished

Arguments sent with this signal:

``sender``
    :class:`djangocms_moderation.models.ModerationCollection` class

``collection``
    A :class:`djangocms_moderation.models.ModerationCollection` instance
    which was submitted to be unpublished.

``moderator``
    A :class:`django.contrib.auth.models.User` associated with the collection which is the moderator of the collection.

``moderation_requests``
    A list of :class:`djangocms_moderation.models.ModerationRequest` instances
    which were unpublished.

    .. note::

        It's possible for this list to contain only some of the requests
        belonging to the collection being moderated,
        because only some of the requests were unpublished.

``workflow``
    An instance of :class:`djangocms_moderation.models.Workflow` which was used for this collection.



How to use the moderation publish signal for a collection
---------------------------------------------------------------------

The CMS used to provide page publish and unpublish signals which have since been removed in DjangoCMS 4.0. You can instead use the signals provided above to replace these.

Djangocms-moderation provides a way to take further actions once a collection has been published. The `published` event is the last event executed for a moderation.


.. code-block:: python

    from django.dispatch import receiver

    from cms.models import PageContent

    from djangocm_moderation.signals import published


    @receiver(published)
    def do_something_on_publish_event(*args, **kwargs):
        # all keyword arguments can be found in kwargs
        # pass

