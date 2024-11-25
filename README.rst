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


Configuration
=============

The following settings can be added to your project's settings file to configure django CMS Moderation's behavior:

``CMS_MODERATION_DEFAULT_COMPLIANCE_NUMBER_BACKEND``
    Default backend used for generating compliance numbers.

``CMS_MODERATION_COMPLIANCE_NUMBER_BACKENDS``
    Dictionary of available compliance number backend classes.

``CMS_MODERATION_ENABLE_WORKFLOW_OVERRIDE``
    Enable or disable workflow override functionality.
    Default: ``False``

``CMS_MODERATION_DEFAULT_CONFIRMATION_PAGE_TEMPLATE``
    Default template used for confirmation pages.

``CMS_MODERATION_CONFIRMATION_PAGE_TEMPLATES``
    List of available confirmation page templates.

``CMS_MODERATION_COLLECTION_COMMENTS_ENABLED``
    Enable or disable comments on collections.
    Default: ``True``

``CMS_MODERATION_REQUEST_COMMENTS_ENABLED``
    Enable or disable comments on moderation requests.
    Default: ``True``

``CMS_MODERATION_COLLECTION_NAME_LENGTH_LIMIT``
    Maximum length for collection names.
    Default: ``255``

``EMAIL_NOTIFICATIONS_FAIL_SILENTLY``
    Control whether email notification errors should be suppressed.
    Default: ``True``

Example Configuration
---------------------

Add these settings to your project's settings file:

.. code-block:: python

    # Enable workflow override
    CMS_MODERATION_ENABLE_WORKFLOW_OVERRIDE = True
    
    # Customize collection name length
    CMS_MODERATION_COLLECTION_NAME_LENGTH_LIMIT = 100
    
    # Disable comment features
    CMS_MODERATION_COLLECTION_COMMENTS_ENABLED = False
    CMS_MODERATION_REQUEST_COMMENTS_ENABLED = False

Documentation
=============

We maintain documentation under ``docs`` folder using rst format. HTML documentation can be generated using the following commands

Run::

    cd docs/
    make html

This should generate all html files from rst documents under the `docs/_build` folder, which can be browsed.
