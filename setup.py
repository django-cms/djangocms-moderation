from setuptools import find_packages, setup

import djangocms_moderation


INSTALL_REQUIREMENTS = [
    "Django>=1.11,<3.0",
    "django-cms",
    "django-sekizai>=0.7",
    "django-admin-sortable2>=0.6.4",
]

TEST_REQUIREMENTS = [
    "djangocms-version-locking",
    "djangocms-versioning",
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
        "https://github.com/divio/django-cms/tarball/release/4.0.x#egg=django-cms-4.0.0",
        "https://github.com/divio/djangocms-versioning/tarball/master#egg=djangocms-versioning-0.0.23",
        "https://github.com/FidelityInternational/djangocms-version-locking/tarball/master#egg=djangocms-version-locking-0.0.13", # noqa
    ]
)
