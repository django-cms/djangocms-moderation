.. _repair_states:

How to repair inconsistent moderation states
============================================

In rare scenarios a version can become un-editable because a
:class:`~djangocms_moderation.models.ModerationRequest` is left in an
inconsistent state: the request still has ``is_active=True`` although its
version has been published and its collection archived. Versioning then
refuses to create a new draft from the published version.

The symptom: the **New Draft** option is missing for a published version,
and the version appears locked by moderation although its collection is
finished.

Diagnose
--------

Run the ``moderation_fix_states`` management command without options to
list affected moderation requests — it changes nothing::

    python manage.py moderation_fix_states

Fix
---

If the analysis lists broken requests, run the command again with the
``--perform-fix`` flag::

    python manage.py moderation_fix_states --perform-fix

This resets ``is_active`` to ``False`` on the affected requests, leaving
version and collection states untouched. The version can then be edited
(via a new draft) again.

.. warning::

    As with any data-repair command, back up your database first and make
    sure you understand why the state became inconsistent — see
    :ref:`management_commands` for details of what the command checks.
