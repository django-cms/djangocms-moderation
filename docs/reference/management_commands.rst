.. _management_commands:

Management Commands
================================================
The commands made available to developers should be used with caution, be sure that you know what you are doing.

moderation_fix_states
-------------------------------------------------
This command is to be used only when a version becomes un-editable due to inconsistencies with states that are controlled by moderation.
It has been observed that the state can end up inconsistent in very rare scenarios. A `ModerationRequest` object should never have `is_active=True` when the item has been successfully published.
The following states can cause a version to be locked from editing:

 - `ModerationRequest.is_active=True`
 - `ModerationRequest.version.state=published`
 - `ModerationRequest.collection.state=Archived`

In this scenario a new Draft object cannot be created from the Published object due to version checks.

The command will first analyse and list any `ModerationRequest` objects that are in a broken / inconsistent state.

The fix will correctly set the is_active flag leaving the correct states:

 - `ModerationRequest.is_active=False`
 - `ModerationRequest.version.state=published`
 - `ModerationRequest.collection.state=Archived`

Usage
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
To first run an analysis on whether any `ModerationRequest` objects have a broken / inconsistent state.

``python manage.py moderation_fix_states``

To execute and resolve any state inconsistencies, you can run the command with the `--perform-fix` flag set.

``python manage.py moderation_fix_states --perform-fix``
