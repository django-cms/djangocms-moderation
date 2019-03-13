.. _overview:

Overview
================================================

Moderation provides an approval workflow mechanism for organisations who need to ensure that content is approved before it is published. It is designed to extend and compliment the Versioning addon and has that as a dependency.

The general idea is that a draft version can be submitted for moderation. This involves adding that draft to a :ref:`collection`, which can be thought of as a chapter, edition or batch of content that aims to all be published simultaneously. Various drafts can be added to the same :ref:`collection`. 

Drafts within the :ref:`collection` can then be approved rejected by various parties according to :ref:`role`s defined within the :ref:`workflow` assigned to the :ref:`collection`.

Once one or more items within the :ref:`collection` have been approved, the :ref:`collection` owner is able to select those items and publish them.

Comments can also be added to any of these entities :ref:`collection`, :ref:`moderation_request`, :ref:`moderation_request_action`.

The Moderation addon makes use of the App Registry features provided as part of DjangoCMS 4.0 in order to register models for various content-types to be moderated. Thus it is possible to configure your CMS project so that some content-types are moderated whilst others are not. Any such model registered with Moderation must also be registered with Versioning.