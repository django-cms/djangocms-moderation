Admin Moderation
==========================


monkeypatch.py
--------------------------
Moderation monkeypatches some of Versioning's admin pages.
`get_state_actions`:- this adds a "Submit for moderation" link next to draft versions in the Version table for a given content-type.

It also adds some checks to the `checks-framework` checks registered in Versioning, to prevent certain Versioning functions at certain stages of moderation.

admin.py
-------------------------
Aside from the usual, there are a number of bulk-action confirmation views that are generated here:- `delete_selected`, `approve`, `rework`, `publish`, `resubmit`. These each provide additional information whilst facilitating confirmation and the `admin_actions.py` redirect to these views.

The available bulk actions are also controlled by the internal permissions system within Moderation which links Users or Groups to Roles. Each :ref:`moderation_request_action` within a :ref:`workflow` has a single :ref:`role` assigned to it. Each :ref:`moderation_collection` has a :ref:`workflow`. The result is that not all bulk-actions will be available to every user and some will appear only when the :ref:`moderation_request` is in a particular inferred state.

cms_toolbars.py
-------------------------
Replaces the VersioningToolbar object with the ModerationToolbar object in order to show Versioning-related buttons at the correct part of the :ref:`workflow`.
