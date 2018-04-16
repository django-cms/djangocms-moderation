from functools import wraps
from threading import local

from django.utils.decorators import available_attrs
from django.utils.translation import get_language

from cms.utils import get_current_site, page_permissions

from .helpers import get_active_moderation_request

# thread local support
_thread_locals = local()


def set_current_language(user):
    _thread_locals.request_language = user


def get_request_language():
    return getattr(_thread_locals, 'request_language', get_language())


def user_can_change_page(func):
    @wraps(func, assigned=available_attrs(func))
    def wrapper(user, page, site=None):
        can_change = func(user, page, site=site)

        if not can_change:
            return can_change

        active_request = get_active_moderation_request(page, get_request_language())

        if active_request:
            return False
        return can_change
    return wrapper


page_permissions.user_can_change_page = user_can_change_page(page_permissions.user_can_change_page)
