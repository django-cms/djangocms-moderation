from functools import lru_cache
from urllib.parse import parse_qs, urljoin

from django.conf import settings
from django.contrib.sites.models import Site
from django.utils.module_loading import import_string
from django.utils.translation import override as force_language

from cms.utils.urlutils import admin_reverse


def get_absolute_url(location, site=None):
    if not site:
        site = Site.objects.get_current()

    if getattr(settings, "USE_HTTPS", False):
        scheme = "https"
    else:
        scheme = "http"
    domain = f"{scheme}://{site.domain}"
    return urljoin(domain, location)


def get_admin_url(name, language, args):
    with force_language(language):
        return admin_reverse(name, args=args)


@lru_cache(maxsize=None)
def load_backend(path):
    return import_string(path)


def generate_compliance_number(path, **kwargs):
    backend = load_backend(path)
    return backend(**kwargs)


def extract_filter_param_from_changelist_url(request, keyname, parametername):
    """
    Searches request.GET for a given key and decodes the value for a particular parameter
    """
    changelist_filters = request.GET.get(keyname)
    parameter_value = parse_qs(changelist_filters).get(parametername)
    try:
        return parameter_value[0]
    except (TypeError, IndexError):
        return None
