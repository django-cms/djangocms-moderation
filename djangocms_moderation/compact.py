from django import get_version

from packaging.version import Version


DJANGO_VERSION = get_version()


DJANGO_4_1 = Version(DJANGO_VERSION) < Version('4.2')
