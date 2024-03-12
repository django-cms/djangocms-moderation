.. _moderation_collection:

Moderation Collection
================================================

A Moderation Collection is primarily intended as a way of being able to group draft content versions together for:
a) review and
b) publishing

The rules for adding items to a Collection, removing items from a Collection and the actions that can be taken on items the Collection may vary by :ref:`workflow`.

Publishing is a `djangocms-versioning` feature, thus `djangocms-moderation` depends on and extends the functionality made available by the Versioning addon.

Collections are stateful. The available states are:
 * Collecting
 * In review
 * Archived
 * Cancelled

Drafts can only be added to a Collection during the `Collecting` phase (see :ref:`lock`)

Buttons
-------------------------------------------------

Add Collection
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Those with permissions can create new collections. The author is auto-assigned as the current user. A :ref:`workflow` must be selected. A name must be given to the collection. If there are already items in the Collection, these will be shown on the confirmation screen.

Edit Collection
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
The selected workflow can only be changed whilst the Collection is in `collecting` state.


Add draft to Collection ("Submit for moderation")
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
The CMSToolbar (for content-types with a preview end-point) will be modified to add the "Submit for moderation" button for draft versions. Doing so allows one to select which Collection to add the draft to.

Actions
-------------------------------------------------

Submit for review
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Moves the collection state from `collecting` to `in review`. Only available whilst collection phase is `collecting`. Sends out notifications to the selected reviewers.

Cancel collection
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Changes the collection state to `cancelled`.

Archive collection
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Changes the collection state to `archived`. Only available if every :ref:`moderation_request` in the Collection has been approved.



States
-------------------------------------------------

Collecting
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Once a Collection is created it is in this initial state, which allows draft versions to be added to a Collection by its author only.

In Review
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
A collection is submitted for review by the collection author. Reviewers (see :ref:`role`) are then able to act on versions in that Collection. Such actions are tracked as a :ref:`moderation_request_action`. Drafts cannot be added to a Moderation Collection while that collection is `in review` and drafts that are already in the Collection have limited editing permissions (see :ref:`lock`).

Archived
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Once all items in a collection have either been removed or approved, the collection becomes archiveable. Archiving a collection is a manual process. The effect of archiving a collection is that it to facilitate list filtering. Archived collections cannot be modified in any way.

Cancelled
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
A collection can also be flagged as cancelled. This is similar to Archived except that it can be done at any stage.




Bulk Actions
-------------------------------------------------
These will appear in the Collection’s action drop-down for each content-type registered with Moderation.

Remove from collection
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Removes a draft from the collection.

Approve
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Flags a draft as being ready for publishing.

Submit for rework (reject)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Flags a draft as being in need of further editing

Submit for review
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Useful for items that have been flagged for rework - resubmits them for review, sending out notifications again.
