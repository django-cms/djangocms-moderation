*********************
django CMS Moderation
*********************

django CMS Moderation adds editorial approval workflows to django CMS: draft
content is gathered into collections, routed through configurable review steps,
and published only once the right people have signed it off. It builds on
`djangocms-versioning <https://github.com/django-cms/djangocms-versioning>`_.

=============
Documentation
=============

Full documentation — tutorial, how-to guides, a complete settings reference and
background explanation — is published at
`djangocms-moderation.readthedocs.io <https://djangocms-moderation.readthedocs.io>`_.

New to moderation? Start with the `quick-start tutorial
<https://djangocms-moderation.readthedocs.io/en/latest/tutorial/quickstart.html>`_,
which takes you from an empty project to a published page in about ten minutes.

============
Installation
============

django CMS Moderation requires a django CMS 4.1 (or higher) project, with
`djangocms-versioning <https://github.com/django-cms/djangocms-versioning>`_
installed.

Run::

    pip install djangocms-moderation

Add the following to your project's ``INSTALLED_APPS``:

- ``'djangocms_moderation'``
- ``'adminsortable2'``

Then run the application's database migrations::

    python manage.py migrate djangocms_moderation

For the full set-up, see the `installation guide
<https://djangocms-moderation.readthedocs.io/en/latest/howto/installation.html>`_.
All configuration options are documented in the `settings reference
<https://djangocms-moderation.readthedocs.io/en/latest/reference/settings.html>`_.

============
Contributing
============

The documentation sources live under ``docs/`` in reStructuredText format. To
build and preview the HTML locally::

    cd docs/
    make html

The generated files appear under ``docs/_build/html`` and can be opened in a
browser. The published site on Read the Docs is rebuilt automatically from the
``docs/`` sources.
