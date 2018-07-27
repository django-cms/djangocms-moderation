HELPER_SETTINGS = {
    'INSTALLED_APPS': [
        'tests.utils.app_1',
        'tests.utils.app_2',
        'djangocms_versioning',
        'filer',
        'easy_thumbnails',
        'absolute',
        'aldryn_forms',
        'captcha',
        'emailit',
    ],
}


def run():
    from djangocms_helper import runner
    runner.cms('djangocms_moderation')


if __name__ == '__main__':
    run()
