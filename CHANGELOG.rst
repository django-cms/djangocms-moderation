=========
Changelog
=========

Unreleased
==========
* fix: Alter burger menu js to prioritise injected static url

2.1.1 (2022-06-24)
==================
* fix: Updated moderation_request_change_list to pass static url for svg asset in burger menu

2.1.0 (2022-06-23)
==================
* feat: Added burgermenu for ModerationRequestTreeAdmin icons
* fix: Avoid errors thrown when nested plugins are M2M fields
* fix: Add to collection should automatically add deeply nested draft versioned objects #205
* fix: Refactor flawed add to collection XSS redirect sanitisation added in 1.0.26

2.0.0 (2022-01-18)
===================
* Python 3.8, 3.9 support added
* Django 3.0, 3.1 and 3.2 support added
* Python 3.5 and 3.6 support removed
* Django 1.11 support removed

1.0.28 (2021-10-18)
===================
* Configuration options added to the cms_config to allow a third party to add fields and actions to the Moderation Request Changelist admin view.
* Flake8 code formatting error fixes

1.0.27 (2021-03-10)
===================
* Wrapped the publish view logic in a transaction to prevent inconsistent ModerationRequest states in the future.
* Added a new management command: "moderation_fix_states" to repair any ModerationRequests left in an inconsistent state where the the is_active state is True, the ModerationRequest version object is published, and the collection is Archived.
