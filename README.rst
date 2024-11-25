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

.. list-table::
   :header-rows: 1
   :widths: 50 50

   * - Setting
     - Description
   * - ``CMS_MODERATION_DEFAULT_COMPLIANCE_NUMBER_BACKEND``
     - Default backend class for generating compliance numbers.
       Default is ``djangocms_moderation.backends.uuid4_backend``.
   * - ``CMS_MODERATION_COMPLIANCE_NUMBER_BACKENDS``
     - List of available compliance number backend classes.
       By default, three backends are configured: ``uuid4_backend``,
       ``sequential_number_backend``, and
       ``sequential_number_with_identifier_prefix_backend``.
   * - ``CMS_MODERATION_ENABLE_WORKFLOW_OVERRIDE``
     - Enable/disable workflow override functionality. Defaults to ``False``.
   * - ``CMS_MODERATION_DEFAULT_CONFIRMATION_PAGE_TEMPLATE``
     - Default template for confirmation pages. Defaults to
       ``djangocms_moderation/moderation_confirmation.html``
   * - ``CMS_MODERATION_CONFIRMATION_PAGE_TEMPLATES``
     - List of available confirmation page templates. Only includes the
       default template by default.
   * - ``CMS_MODERATION_COLLECTION_COMMENTS_ENABLED``
     - Enable/disable comments on collections. Defaults to ``True``.
   * - ``CMS_MODERATION_REQUEST_COMMENTS_ENABLED``
     - Enable/disable comments on requests. Defaults to ``True``.
   * - ``CMS_MODERATION_COLLECTION_NAME_LENGTH_LIMIT``
     - Maximum length for collection names. Defaults to ``24``.
   * - ``EMAIL_NOTIFICATIONS_FAIL_SILENTLY``
     - Control email notification error handling. Defaults to ``False``.

Example Configuration
---------------------

Add these settings to your project's settings file:

.. code-block:: python

    # Custom compliance number backend
    CMS_MODERATION_DEFAULT_COMPLIANCE_NUMBER_BACKEND = 'myapp.backends.CustomComplianceNumberBackend'

    # Enable workflow override
    CMS_MODERATION_ENABLE_WORKFLOW_OVERRIDE = True

    # Custom confirmation template
    CMS_MODERATION_DEFAULT_CONFIRMATION_PAGE_TEMPLATE = 'custom_confirmation.html'

    # Enable comments
    CMS_MODERATION_COLLECTION_COMMENTS_ENABLED = True
    CMS_MODERATION_REQUEST_COMMENTS_ENABLED = True

    # Set collection name length limit
    CMS_MODERATION_COLLECTION_NAME_LENGTH_LIMIT = 100

    # Control email notification errors
    EMAIL_NOTIFICATIONS_FAIL_SILENTLY = False

=============
Documentation
=============

We maintain documentation under ``docs`` folder using rst format. HTML documentation can be generated using the following commands

Run::

    cd docs/
    make html

This should generate all html files from rst documents under the `docs/_build` folder, which can be browsed.
