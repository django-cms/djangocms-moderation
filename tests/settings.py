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
        'djangocms_text_ckeditor',
        'djangocms_versioning.test_utils.polls',
        'djangocms_versioning.test_utils.blogpost',
        'djangocms_versioning.test_utils.people',
    ],
}


def run():
    from djangocms_helper import runner
    runner.cms('djangocms_moderation')


if __name__ == '__main__':
    run()
