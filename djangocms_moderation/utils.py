from __future__ import unicode_literals

from django.conf import settings
from django.contrib.sites.models import Site
from django.utils.lru_cache import lru_cache
from django.utils.module_loading import import_string
from django.utils.six.moves.urllib.parse import parse_qs, urljoin
from django.utils.translation import override as force_language

from cms.utils.urlutils import admin_reverse

from djangocms_versioning.models import Version


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


def generate_compliance_number(path, **kwargs):
    backend = load_backend(path)
    return backend(**kwargs)


def extract_filter_param_from_changelist_url(request, keyname, parametername):
    """
    Searches request.GET for a given key and decodes the value for a particular parameter
    """
    changelist_filters = request.GET.get(keyname)
    parameter_value = parse_qs(changelist_filters).get(parametername)
    return parameter_value[0]


def is_obj_review_locked(obj, user):
    """
    Util function which determines if the `obj` is Review locked.
    It is the equivalent of "Can `user` edit the version of object `obj`"?
    """
    moderation_request = get_active_moderation_request(obj)
    if not moderation_request:
        return False

    # If `user` can resubmit the moderation request, it means they can edit
    # the version to submit the changes. Review lock should be lifted for them
    if moderation_request.user_can_resubmit(user):
        return False
    return True


def get_active_moderation_request(content_object):
    """
    If this returns None, it means there is no active_moderation request for this
    object, and it means it can be submitted for moderation
    """
    from djangocms_moderation.models import ModerationRequest  # noqa
    version = Version.objects.get_for_content(content_object)

    try:
        return ModerationRequest.objects.get(
            version=version, is_active=True
        )
    except ModerationRequest.DoesNotExist:
        return None
