HELPER_SETTINGS = {
    'INSTALLED_APPS': [
        'tests.utils.app_1',
        'tests.utils.app_2',
        'djangocms_versioning',
        'djangocms_version_locking',
        'filer',
        'easy_thumbnails',
        'absolute',
        'aldryn_forms',
        'captcha',
        'emailit',
        'djangocms_text_ckeditor',
        'djangocms_versioning.test_utils.polls',
        'djangocms_versioning.test_utils.blogpost',
        'djangocms_versioning.test_utils.people',
        'djangocms_versioning.test_utils.text',
    ],
    # As adviced, we can disable migrations in tests. This will improve
    # test performance and removes the need for test apps to provide migrations
    'MIGRATION_MODULES': {
        'auth': None,
        'cms': None,
        'menus': None,
        'djangocms_versioning': None,
        'djangocms_version_locking': None,
        'filer': None,
        'djangocms_moderation': None,
        'aldryn_forms': None,
    },
}


def run():
    from djangocms_helper import runner
    runner.cms('djangocms_moderation')


if __name__ == '__main__':
    run()
