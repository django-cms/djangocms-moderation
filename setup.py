from setuptools import find_packages, setup

import djangocms_moderation


INSTALL_REQUIREMENTS = [
    "Django>=1.8,<2.0",
    "django-cms>=3.4.2",
    "django-sekizai>=0.7",
    "django-admin-sortable2>=0.6.4",
]

TEST_REQUIREMENTS = [
    "aldryn-forms",
    "django-cms",
    "pillow<=5.4.1",  # Requirement for tests to pass in python 3.4
    "lxml<=4.3.5",  # Requirement for tests to pass in python 3.4
    "djangocms-text-ckeditor",
    "djangocms-version-locking",
    "djangocms-versioning",
    "djangocms_helper",
    "factory-boy",
    "mock"
]

setup(
    name="djangocms-moderation",
    packages=find_packages(),
    include_package_data=True,
    version=djangocms_moderation.__version__,
    description=djangocms_moderation.__doc__,
    long_description=open("README.rst").read(),
    classifiers=[
        "Framework :: Django",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: BSD License",
        "Operating System :: OS Independent",
        "Topic :: Software Development",
    ],
    install_requires=INSTALL_REQUIREMENTS,
    author="Divio AG",
    author_email="info@divio.ch",
    url="http://github.com/divio/djangocms-moderation",
    license="BSD",
    tests_require=TEST_REQUIREMENTS,
    test_suite="tests.settings.run",
    dependency_links=[
        "http://github.com/divio/django-cms/tarball/release/4.0.x#egg=django-cms-4.0.0",
        "http://github.com/divio/djangocms-versioning/tarball/master#egg=djangocms-versioning-0.0.23",
        "http://github.com/FidelityInternational/djangocms-version-locking/tarball/master#egg=djangocms-version-locking-0.0.13", # noqa
        "https://github.com/divio/djangocms-text-ckeditor/tarball/support/4.0.x#egg=djangocms-text-ckeditor-4.0.x",
        "https://github.com/divio/aldryn-forms/tarball/master#egg=aldryn-forms"
    ]
)
