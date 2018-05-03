from __future__ import unicode_literals
from functools import lru_cache

from django.core.urlresolvers import reverse
from django.conf import settings
from django.contrib.sites.models import Site
from django.utils.module_loading import import_string
from django.utils.six.moves.urllib.parse import urljoin
from django.utils.translation import override as force_language

from cms.utils.urlutils import admin_reverse

from aldryn_forms.models import FormSubmission


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


@lru_cache(maxsize=None)
def load_backend(path):
    return import_string(path)


def generate_reference_number(path, **kwargs):
    backend = load_backend(path)
    return backend(**kwargs)


def get_action_form_submission_url(form_pk):
    opts = FormSubmission._meta
    return reverse(
        'admin:{}_{}_change'.format(opts.app_label, opts.model_name),
        args=[form_pk]
    )