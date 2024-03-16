from setuptools import find_packages, setup

import djangocms_moderation


INSTALL_REQUIREMENTS = [
    "Django>=3.2",
    "django-cms",
    "django-sekizai>=0.7",
    "django-admin-sortable2>=0.6.4",
]
DEPENDENCY_LINKS = [
    "https://github.com/django-cms/django-cms/tarball/release/4.0.1.x#egg=django-cms",
    "https://github.com/django-cms/djangocms-versioning/tarball/1.2.2#egg=djangocms-versioning",
]

setup(
    name="djangocms-moderation",
    packages=find_packages(),
    include_package_data=True,
    version=djangocms_moderation.__version__,
    description=djangocms_moderation.__doc__,
    long_description=open("README.rst").read(),
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        "Programming Language :: Python",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Framework :: Django",
        "Framework :: Django :: 3.2",
        "Framework :: Django :: 4.2",
        "Framework :: Django :: 5.0",
        "Framework :: Django CMS",
        "Framework :: Django CMS :: 4.0",
        "Framework :: Django CMS :: 4.1",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: BSD License",
        "Operating System :: OS Independent",
        "Topic :: Software Development",
    ],
    install_requires=INSTALL_REQUIREMENTS,
    dependency_links=DEPENDENCY_LINKS,
    author="Divio AG",
    author_email="info@divio.ch",
    maintainer='Django CMS Association and contributors',
    maintainer_email='info@django-cms.org',
    url="https://github.com/django-cms/djangocms-moderation",
    license="BSD",
    test_suite="tests.settings.run",
)
