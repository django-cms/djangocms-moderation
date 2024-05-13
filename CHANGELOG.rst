=========
Changelog
=========

Unreleased
==========

* fix: Workflow admin view by removing django admin sortable2
* fix: Treebeard support improved by inheriting a treebeard template

2.1.6 (2022-09-07)
==================
* fix: Language max_length too short for certain language codes

2.1.5 (2022-07-11)
==================
* fix: Broken markup in the ModerationCollection changelist view, and missing attributes in the burger menu

2.1.4 (2022-07-08)
==================
* fix: Broken markup and js scripts in the ModerationRequest changelist views

2.1.3 (2022-06-24)
==================
* fix: Retain classes which define whether a link should open in a modal or not

2.1.2 (2022-06-24)
==================
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
