from tempfile import mkdtemp


def gettext(s):
    return s


SECRET_KEY = "moderationtestsuitekey"

DEBUG = False

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}

ROOT_URLCONF = "tests.urls"

SITE_ID = 1

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.auth",
    "django.contrib.sessions",
    "django.contrib.sites",
    "django.contrib.staticfiles",
    "django.contrib.messages",
    "djangocms_admin_style",
    "django.contrib.admin",
    # django CMS and its dependencies
    "cms",
    "menus",
    "treebeard",
    "sekizai",
    # related applications
    "filer",
    "easy_thumbnails",
    "captcha",
    "djangocms_versioning",
    "djangocms_text",
    "djangocms_alias",
    # the application under test
    "djangocms_moderation",
    # test applications
    "tests.utils.app_1",
    "tests.utils.app_2",
    "tests.utils.moderated_polls",
    "tests.utils.versioned_none_moderated_app",
]

MIDDLEWARE = [
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "cms.middleware.user.CurrentUserMiddleware",
    "cms.middleware.page.CurrentPageMiddleware",
    "cms.middleware.toolbar.ToolbarMiddleware",
    "cms.middleware.language.LanguageCookieMiddleware",
]

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "django.template.context_processors.i18n",
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.template.context_processors.media",
                "django.template.context_processors.csrf",
                "django.template.context_processors.tz",
                "django.template.context_processors.static",
                "cms.context_processors.cms_settings",
                "sekizai.context_processors.sekizai",
            ],
        },
    },
]

LANGUAGE_CODE = "en"
LANGUAGES = (
    ("en", gettext("English")),
    ("de", gettext("German")),
    ("fr", gettext("French")),
    ("it", gettext("Italiano")),
)
CMS_LANGUAGES = {
    1: [
        {"code": "en", "name": gettext("English"), "public": True},
        {"code": "de", "name": gettext("German"), "public": True},
        {"code": "fr", "name": gettext("French"), "public": True},
        {"code": "it", "name": gettext("Italiano"), "public": True},
    ],
    "default": {"hide_untranslated": False},
}

CMS_TEMPLATES = (
    ("fullwidth.html", "Fullwidth"),
    ("page.html", "Normal page"),
)
CMS_CONFIRM_VERSION4 = True

DJANGOCMS_VERSIONING_LOCK_VERSIONS = True

THUMBNAIL_PROCESSORS = (
    "easy_thumbnails.processors.colorspace",
    "easy_thumbnails.processors.autocrop",
    "filer.thumbnail_processors.scale_and_crop_with_subject_location",
    "easy_thumbnails.processors.filters",
)

STATIC_URL = "/static/"
MEDIA_URL = "/media/"
MEDIA_ROOT = mkdtemp()
FILE_UPLOAD_TEMP_DIR = mkdtemp()

USE_TZ = True
TIME_ZONE = "UTC"

DEFAULT_AUTO_FIELD = "django.db.models.AutoField"

PASSWORD_HASHERS = ("django.contrib.auth.hashers.MD5PasswordHasher",)

CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}

EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

TESTS_RUNNING = True
