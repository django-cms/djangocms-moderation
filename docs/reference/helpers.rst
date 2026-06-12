.. _helpers:

Python API
==========

Helper functions for third-party code that needs to interact with
moderation — for example a custom admin, toolbar or REST endpoint that must
respect review locks. All functions live in
``djangocms_moderation.helpers``.

.. py:function:: is_registered_for_moderation(content_object)

   Return ``True`` if the content object's model is registered for
   moderation via any app's ``moderated_models`` (see :ref:`cms_config`).

.. py:function:: get_active_moderation_request(content_object)

   Return the active :class:`~djangocms_moderation.models.ModerationRequest`
   for the content object's version, or ``None`` if there is none — meaning
   the object can be submitted for moderation.

.. py:function:: is_obj_review_locked(obj, user)

   Return ``True`` if ``obj`` is review-locked for ``user``, i.e. the user
   must not edit the version because it is part of an active moderation
   request. The lock is lifted for the author of a rejected request, who
   needs to edit the content in order to resubmit it (see :ref:`lock`).

.. py:function:: is_obj_version_unlocked(content_obj, user)

   Return ``True`` if the content object is not version-locked for the
   user. Takes djangocms-version-locking into account when that package is
   installed; without it, always returns ``True``.

.. py:function:: get_page_or_404(obj_id, language)

   Return the ``PageContent`` for the given page id and language, or raise
   ``Http404``.

Signals
-------

For reacting to moderation events (submission, publication, unpublication)
see :ref:`signals`.
