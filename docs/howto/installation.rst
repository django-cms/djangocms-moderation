.. _installation:

How to install moderation in an existing project
=================================================

Requirements
------------

* django CMS 4.0 or higher
* `djangocms-versioning <https://github.com/django-cms/djangocms-versioning>`_
  — moderation works on draft *versions*, so versioning is a hard dependency

Installation
------------

Install the package from PyPI::

    pip install djangocms-moderation

Add the apps to ``INSTALLED_APPS`` in your settings::

    INSTALLED_APPS = [
        ...
        "djangocms_versioning",
        "djangocms_moderation",
        "adminsortable2",
        ...
    ]

Run the migrations::

    python manage.py migrate djangocms_moderation

Restart your server. Pages (``PageContent``) are registered for moderation
out of the box — a **django CMS Moderation** section appears in the admin
and draft pages gain a **Submit for moderation** toolbar button.

To moderate your own content types as well, see :ref:`moderating_models`.
For the available settings, see :ref:`settings`.

.. note::

    Once moderation is installed, the **Publish** button that
    djangocms-versioning normally shows on drafts is replaced by the
    moderation workflow for all registered models: content must go through
    a collection to be published.
