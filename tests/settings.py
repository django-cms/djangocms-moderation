from cms import __version__ as cms_version


HELPER_SETTINGS = {
    "SECRET_KEY": "moderationtestsuitekey",
    "INSTALLED_APPS": [
        "tests.utils.app_1",
        "tests.utils.app_2",
        "djangocms_versioning",
        # the following 4 apps are related
        "filer",
        "easy_thumbnails",
        "captcha",
        "djangocms_alias",
        "djangocms_text_ckeditor",
        "tests.utils.moderated_polls",
        "tests.utils.versioned_none_moderated_app",
    ],
    # As advised, we can disable migrations in tests. This will improve
    # test performance and removes the need for test apps to provide migrations
    "MIGRATION_MODULES": {
        "auth": None,
        "cms": None,
        "menus": None,
        "djangocms_alias": None,
        "djangocms_versioning": None,
        "djangocms_version_locking": None,
        "filer": None,
        "djangocms_moderation": None,
        "djangocms_text_ckeditor": None,
    },
    "DEFAULT_AUTO_FIELD": "django.db.models.AutoField",
    "DJANGOCMS_VERSIONING_LOCK_VERSIONS": True,
    "CMS_CONFIRM_VERSION4": True,
}

if cms_version < "4.1.0":
    HELPER_SETTINGS["INSTALLED_APPS"].append("djangocms_version_locking")


def run():
    from djangocms_helper import runner

    runner.cms("djangocms_moderation")


if __name__ == "__main__":
    run()
