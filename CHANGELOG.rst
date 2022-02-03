=========
Changelog
=========

Unreleased
==========
* fix: Add to collection should automatically add deeply nested draft versioned objects #205

1.0.29 (2022-01-18)
===================
* fix: Refactor flawed add to collection XSS redirect sanitisation added in 1.0.26
* Pin the following packages to a python 3.6 compatible version matching this release stream: django-admin-sortable2, djangocms-text-ckeditor, djangocms-version-locking and djangocms-versioning.

1.0.28 (2021-10-18)
===================
* Configuration options added to the cms_config to allow a third party to add fields and actions to the Moderation Request Changelist admin view.
* Flake8 code formatting error fixes

1.0.27 (2021-03-10)
===================
* Wrapped the publish view logic in a transaction to prevent inconsistent ModerationRequest states in the future.
* Added a new management command: "moderation_fix_states" to repair any ModerationRequests left in an inconsistent state where the the is_active state is True, the ModerationRequest version object is published, and the collection is Archived.
