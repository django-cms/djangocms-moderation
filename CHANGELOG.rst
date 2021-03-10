=========
Changelog
=========

Unreleased
==========

1.0.27 (2021-03-10)
==================
* Wrapped the publish view logic in a transaction to prevent inconsistent ModerationRequest states in the future.
* Added a new management command: "moderation_fix_states" to repair any ModerationRequests left in an inconsistent state where the the is_active state is True, the ModerationRequest version object is published, and the collection is Archived.
