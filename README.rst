*********************
django CMS Moderation
*********************

============
Installation
============

Requirements
============

django CMS Moderation requires that you have a django CMS 4.0 (or higher) project already running and set up.

djangocms-versioning is also required along with django-fsm which should be installed with versioning.


To install
==========

Run::

    pip install git+git://github.com/django-cms/djangocms-moderation@master#egg=djangocms-moderation

Add the following to your project's ``INSTALLED_APPS``:

  - ``'djangocms_moderation'``
  - ``'adminsortable2'``

Run::

    python manage.py migrate djangocms_moderation

to perform the application's database migrations.

Documentation
=============

We maintain documentation under ``docs`` folder using rst format. HTML documentation can be generated using the following commands

Run::

    cd docs/
    make html

This should generate all html files from rst documents under the `docs/_build` folder, which can be browsed.
