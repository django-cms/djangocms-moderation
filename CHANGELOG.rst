=========
Changelog
=========

Unreleased
==========
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
