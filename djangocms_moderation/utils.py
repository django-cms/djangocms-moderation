from __future__ import unicode_literals
import importlib

from django.conf import settings
from django.contrib.sites.models import Site
from django.utils.six.moves.urllib.parse import urljoin
from django.utils.translation import override as force_language

from cms.utils.urlutils import admin_reverse


def get_absolute_url(location, site=None):
    if not site:
        site = Site.objects.get_current()

    if getattr(settings, 'USE_HTTPS', False):
        scheme = 'https'
    else:
        scheme = 'http'
    domain = '{}://{}'.format(scheme, site.domain)
    return urljoin(domain, location)


def get_admin_url(name, language, args):
    with force_language(language):
        return admin_reverse(name, args=args)


def get_moderation_workflow_selectable_settings():
    if hasattr(settings, 'CMS_MODERATION_WORKFLOW_SELECTABLE'):
        return settings.CMS_MODERATION_WORKFLOW_SELECTABLE
    return False


def call_method_from_string(function_string, **kwargs):
    mod_name, func_name = function_string.rsplit('.', 1)
    mod = importlib.import_module(mod_name)
    func = getattr(mod, func_name)
    result = func(**kwargs)
    return result
