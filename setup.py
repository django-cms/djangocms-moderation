from setuptools import find_packages, setup

import djangocms_moderation


INSTALL_REQUIREMENTS = [
    "Django>=2.2,<4.0",
    "django-cms",
    "django-sekizai>=0.7",
    "django-admin-sortable2>=0.6.4",
]

TEST_REQUIREMENTS = [
    "djangocms-alias",
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
    tests_require=TEST_REQUIREMENTS,
    author="Divio AG",
    author_email="info@divio.ch",
    maintainer='Django CMS Association and contributors',
    maintainer_email='info@django-cms.org',
    url="http://github.com/django-cms/djangocms-moderation",
    license="BSD",
    test_suite="tests.settings.run",
    dependency_links=[
        "https://github.com/django-cms/djangocms-alias.git",
    ]
)
