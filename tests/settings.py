HELPER_SETTINGS = {
    'INSTALLED_APPS': [
        'filer',
        'easy_thumbnails',
        'djangocms_moderation.contrib.moderation_forms',
        'absolute',
        'aldryn_forms',
        'aldryn_forms.contrib.email_notifications',
        'captcha',
        'emailit',
    ],
}


def run():
    from djangocms_helper import runner
    runner.cms('djangocms_moderation')


if __name__ == '__main__':
    run()
