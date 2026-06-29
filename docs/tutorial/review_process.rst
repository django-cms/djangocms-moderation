.. _tutorial-review-process:

Part 2: A real review process
=============================

In :ref:`part one <tutorial-quickstart>` you published a page through
moderation, but you acted as author *and* reviewer. In a real organisation
those are different people: an editor writes, and someone else signs the
content off. In this part you will add a separate reviewer, route a new
collection through them, and meet the features you would use day to day.

This part continues in the same ``testproj`` project from part one and takes
about twenty minutes.

Create a reviewer
-----------------

Reviewers are usually managed as a group, so you can add or remove people
without touching every workflow. A reviewer needs only to *view* collections
and the requests inside them — crucially, **the ability to approve comes from
the role, not from Django permissions** (more on that below).

#. In the admin, go to **Authentication and Authorization → Groups** and add
   a group called ``Reviewers``. In the permission filter, type ``moderation``
   and grant the group exactly these two permissions:

   * ``djangocms_moderation | collection | Can view collection``
   * ``djangocms_moderation | moderation request tree node | Can view
     moderation request tree node``

   Save the group.
#. Go to **Users → Add user** and create a user called ``reviewer``. Tick
   **Staff status** so they can reach the admin, add them to the ``Reviewers``
   group, and save.

.. note::

    That is the complete permission set for a reviewer. They cannot add, edit
    or delete collections; they can only open them and act on the requests
    they are responsible for. See :ref:`role` for the full picture of how
    moderation's roles and Django permissions interact.

Give reviewers a role and workflow
----------------------------------

A :term:`Role` points moderation at *who* reviews a step. In part one the
role pointed at a single user; this time it points at the whole group.

#. Go to **django CMS Moderation → Roles → Add Role**, name it
   ``Content reviewers``, select the ``Reviewers`` **group** (leave *User*
   empty) and save.
#. Go to **django CMS Moderation → Workflows → Add Workflow**, name it
   ``Standard approval``, tick **Is default** (replacing the quick workflow
   from part one), add one step assigned to the ``Content reviewers`` role and
   save.

   .. image:: /_static/tutorial/03-add-workflow.png
      :width: 100%
      :alt: Adding a Workflow with one step assigned to the Content reviewers role

Organisations with more elaborate sign-off (legal, compliance, marketing …)
add one step per approving party; the request then moves from step to step,
notifying each role in turn. See :ref:`workflow`.

Submit content for review
-------------------------

Set up a fresh collection just as you did in part one, this time using the
new workflow:

#. Add a collection named ``Summer campaign`` using the ``Standard approval``
   workflow.
#. Create a page, and from its toolbar choose **Submit for moderation** and
   add it to the ``Summer campaign`` collection.

   .. image:: /_static/tutorial/06-add-to-collection.png
      :width: 100%
      :alt: The "Add to collection" dialog

   .. note::

       When you add a page, any moderated draft content used by plugins on it
       (for example aliased content) is added to the collection too, so
       reviewers always see the complete picture.

#. Open the collection's requests view (the requests icon in the **actions**
   column) and click **Submit collection for review**:

   .. image:: /_static/tutorial/07-collection-items.png
      :width: 100%
      :alt: The collection's moderation requests with the Submit collection for review button

#. You are asked which review group the first step should notify — choose the
   reviewers and submit:

   .. image:: /_static/tutorial/08-submit-for-review.png
      :width: 100%
      :alt: Selecting the review group when submitting a collection for review

Two things happen: the collection's status changes to *In review* — its
drafts can no longer be added to or edited, they are
:ref:`review-locked <lock>` — and the reviewers are notified by email (check
the runserver console).

Review as a different user
--------------------------

Now switch hats. Log out (or use a private browser window) and log in as
``reviewer``.

Open **django CMS Moderation → Collections → Summer campaign** requests. As a
reviewer you see the pending request, *Pending Content reviewers approval*.
Use the eye icon in the **Preview** column to inspect the content, then tick
the request, choose **Approve** in the action dropdown and click **Run**:

.. image:: /_static/tutorial/09-reviewer-approve.png
   :width: 100%
   :alt: The reviewer selects the moderation request and the Approve action

A confirmation screen summarises what you are approving:

.. image:: /_static/tutorial/10-approve-confirm.png
   :width: 100%
   :alt: The approval confirmation screen

Confirm. The request becomes *Ready for publishing* and the collection author
is notified by email. Had the content needed changes, you would have chosen
**Submit for rework** instead, sending it back to the author with a comment.

Publish
-------

Switch back to your superuser (the author). Open the ``Summer campaign``
requests view, select the approved request, choose **Publish**, click **Run**
and confirm. The page goes live, and because every request in the collection
has now been moderated, the collection archives itself:

.. image:: /_static/tutorial/13-published.png
   :width: 100%
   :alt: The published request in the archived collection

What you have learned
---------------------

* **Reviewers** need only *view* permission on collections and requests; the
  power to approve comes from their **Role**, not from Django permissions.
* **Roles** point at a user or a group; **Workflows** chain one or more
  **steps**, each assigned to a role; the default workflow is used for new
  collections.
* Submitting a collection for review **locks** its content and notifies the
  reviewers of the first step.
* Reviewers **approve** or **send back for rework**; the author **publishes**
  approved content; fully moderated collections archive themselves.

Where to go next
----------------

* :ref:`Enable moderation for your own content types <moderating_models>`
* :ref:`Build multi-step workflows and understand roles in depth <role>`
* :ref:`Customise the notification emails <customize_notifications>`
* :ref:`Generate compliance numbers for approved content <compliance_numbers>`
