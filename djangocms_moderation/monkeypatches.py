from functools import wraps
from threading import local

from django.utils.decorators import available_attrs
from django.utils.translation import get_language

from cms.utils import get_current_site, page_permissions
from cms.utils.conf import get_cms_setting
from cms.utils.permissions import cached_func

from .helpers import get_page_moderation_workflow

# thread local support
_thread_locals = local()


def set_current_language(user):
    _thread_locals.request_language = user


def get_request_language():
    return getattr(_thread_locals, 'request_language', get_language())


@cached_func
@page_permissions.auth_permission_required('change_page', manual=True)
@page_permissions.auth_permission_required('publish_page', manual=True)
def user_can_publish_page(user, page, site=None):
    site = site or get_current_site()

    if not not page.site_is_secondary(site):
        return False

    if user.is_superuser:
        has_perm = True
    elif get_cms_setting('PERMISSION'):
        can_change = page_permissions.has_generic_permission(
            page=page,
            user=user,
            action='change_page',
            site=site,
        )
        has_perm = can_change and page_permissions.has_generic_permission(
            page=page,
            user=user,
            action='publish_page',
            site=site,
        )
    else:
        has_perm = True
    return has_perm


def user_can_change_page(func):
    @wraps(func, assigned=available_attrs(func))
    def wrapper(user, page, site=None):
        can_change = func(user, page, site=site)

        if not can_change:
            return can_change

        workflow = get_page_moderation_workflow(page)

        if workflow and workflow.has_active_request(page, get_request_language()):
            return False
        return can_change
    return wrapper


page_permissions.user_can_change_page = user_can_change_page(page_permissions.user_can_change_page)
page_permissions.user_can_publish_page = user_can_publish_page
