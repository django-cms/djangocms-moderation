*********************
django CMS Moderation
*********************


Requirements
============

django CMS Moderation requires that you have a django CMS 3.4.3 (or higher) project already running and set up.


To install
==========

Run::

    pip install git+git://github.com/divio/djangocms-moderation@develop#egg=djangocms-moderation

Add the following to your project's ``INSTALLED_APPS``:

  - ``'djangocms_moderation'``
  - ``'adminsortable2'``

Run::

    python manage.py migrate djangocms_moderation

to perform the application's database migrations.


To contribute
=============

We need to install the `djangocms 3.4.3` (or higher) and then add this repository as a dependency:

1. Create and activate new virtual env, e.g.

    `mkvirtualenv testenv`

2. Create a project folder, e.g.

    `mkdir ~/workspace/testproject/`

3. `cd ~/workspace/testproject`

4. Install djangocms

    `pip install djangocms-installer`

5. Setup djangocms, e.g.

    `djangocms -f -p . testsite`

6. `pip install djangocms_helper`

7. Add the following email settings to settings.py

::

    # This will ensure that emails will be printed to the console instead of real send
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

::

9. Fork `https://github.com/divio/djangocms-moderation`

10. Clone yours ``djangocms-moderation`` app from github into separate folder,
    e.g. ``~/workspace/djangocms-moderation/``

11. Go to the main project folder  ``cd ~/workspace/testproject`` and install the
    package from your local folder

    `pip install -e ~/workspace/djangocms-moderation/`

12. Add ``djangocms_moderation`` and ``adminsortable2`` to the INSTALLED_APPS in settings.py

13. `python manage.py migrate`

14. Running tests - you can do this straight from your ``~/workspace/djangocms-moderation/``
directory by running

    You might need to install `pip install djangocms-helper`
    `python setup.py test`

Now you can make changes to your local `~/workspace/djangocms-moderation/`
repository and changes will be reflected in your `testproject`.
