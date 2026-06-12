.. _compliance_numbers:

How to generate compliance numbers
==================================

Regulated organisations often need an audit reference for every piece of
approved content. Moderation can stamp each :term:`Moderation Request` with
a unique **compliance number** the moment it receives its final required
approval.

Enable compliance numbers for a workflow
----------------------------------------

Compliance numbers are configured per :term:`Workflow`. In
**django CMS Moderation → Workflows**, edit the workflow and:

#. tick **Requires compliance number?**,
#. choose a **compliance number backend** (see below),
#. optionally set an **identifier** — a free-form prefix used by the
   prefixed backend.

From then on, every request approved through this workflow carries a
compliance number, visible in the moderation request admin.

Built-in backends
-----------------

``djangocms_moderation.backends.uuid4_backend``
    A random 32-character hexadecimal string (default). Globally unique,
    not sequential.

``djangocms_moderation.backends.sequential_number_backend``
    The moderation request's primary key — readable, ascending numbers
    (with gaps).

``djangocms_moderation.backends.sequential_number_with_identifier_prefix_backend``
    Like the sequential backend, prefixed with the workflow's
    **identifier** field, e.g. ``LEGAL-1234``.

Write your own backend
----------------------

A backend is a plain function that receives the moderation request as a
keyword argument and returns a string:

.. code-block:: python

    # myapp/backends.py
    def year_prefixed_backend(**kwargs):
        moderation_request = kwargs["moderation_request"]
        year = moderation_request.date_sent.year
        return f"{year}-{moderation_request.pk:06d}"

Register it in your settings so it appears in the workflow admin's
backend dropdown::

    CMS_MODERATION_COMPLIANCE_NUMBER_BACKENDS = (
        ("myapp.backends.year_prefixed_backend", "Year-prefixed number"),
        ("djangocms_moderation.backends.uuid4_backend", "Unique alphanumeric string"),
    )

    # optional: make it the default for new workflows
    CMS_MODERATION_DEFAULT_COMPLIANCE_NUMBER_BACKEND = (
        "myapp.backends.year_prefixed_backend"
    )

The returned value must be unique across all moderation requests — it is
stored in a unique database column.
