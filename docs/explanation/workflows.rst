.. _workflow:

Workflows and Steps
===================

A **Workflow** describes the approval process a :term:`Moderation
Collection` has to pass: an ordered series of steps, each reviewed by a
:term:`Role`. If your organisation requires sign-off from, say, *marketing*,
*legal* and *compliance*, the workflow has three steps, each assigned to
the corresponding role — and content cannot be published until every
required step has approved it.

Workflows are created and managed in the admin under
**django CMS Moderation → Workflows**. A project can define any number of
them; each collection picks one when it is created. The workflow marked
**is default** is preselected for new collections (only one workflow can
be the default).

.. _workflow_step:

Steps
-----

Each workflow has at least one step, edited inline on the workflow admin
page. A step consists of:

* a **role** — the user or group expected to review at this step (the same
  role can only appear once per workflow);
* an **is mandatory** flag — a request is publishable once every
  *mandatory* step has approved it; steps with the flag unticked may
  review, but do not block publication;
* an **order** — steps are processed top to bottom; reviewers of step two
  are only notified once step one has approved.

For example, an organisation where each department must approve every
request would:

#. set up a user group per department,
#. create one workflow,
#. add one step per department, assigning the department's group as the
   step's role.

Compliance numbers
------------------

A workflow can stamp every fully approved request with a unique audit
reference. The **requires compliance number?** flag, the backend choice and
the free-form **identifier** field (used as a prefix by one of the built-in
backends) control this — see :ref:`compliance_numbers`.
