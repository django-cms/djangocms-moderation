from setuptools import find_packages, setup

import djangocms_moderation


INSTALL_REQUIREMENTS = [
    'Django>=1.8,<1.11',
    'django-cms>=3.4.2',
    'django-sekizai>=0.7',
    'django-admin-sortable2>=0.6.4',
]


setup(
    name='djangocms-moderation',
    packages=find_packages(),
    include_package_data=True,
    version=djangocms_moderation.__version__,
    description=djangocms_moderation.__doc__,
    long_description=open('README.rst').read(),
    classifiers=[
        'Framework :: Django',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Topic :: Software Development'
    ],
    install_requires=INSTALL_REQUIREMENTS,
    author='Divio AG',
    author_email='info@divio.ch',
    url='http://github.com/divio/djangocms-moderation',
    license='BSD',
)
