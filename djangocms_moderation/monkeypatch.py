from django.utils.html import format_html
from django.utils.translation import ugettext_lazy as _

from cms.models import fields
from cms.utils.urlutils import add_url_parameters

from djangocms_versioning.admin import VersionAdmin
from djangocms_versioning.constants import DRAFT
from djangocms_versioning.helpers import version_list_url

from .helpers import (
    get_active_moderation_request,
    get_moderation_button_title_and_url,
    is_obj_review_locked,
    is_obj_version_unlocked,
    is_registered_for_moderation,
)
from .utils import get_admin_url


def get_state_actions(func):
    """
    Monkey patch VersionAdmin's get_state_actions to remove publish link,
    as we don't want publishing CMSToolbar button in moderation.
    + Add moderation link
    """
    def inner(self):
        links = func(self)
        links = [link for link in links if link != self._get_publish_link]
        return links + [self._get_moderation_link]
    return inner


def _get_moderation_link(self, version, request):
    if not is_registered_for_moderation(version.content):
        return ''

    if version.state != DRAFT:
        return ''

    content_object = version.content
    moderation_request = get_active_moderation_request(content_object)
    if moderation_request:
        title, url = get_moderation_button_title_and_url(moderation_request)
        return format_html(
            '<a href="{}">{}</a>',
            url,
            title
        )
    elif is_obj_version_unlocked(content_object, request.user):
        url = add_url_parameters(
            get_admin_url(
                name='cms_moderation_items_to_collection',
                language='en',
                args=()
            ),
            version_ids=version.pk,
            return_to_url=version_list_url(version.content)
        )
        # TODO use a fancy icon as for the rest of the actions?
        return format_html(
            '<a href="{}">{}</a>',
            url,
            _('Submit for moderation')
        )
    return ''


def _get_edit_link(func):
    """
    Don't display edit link if the object is review locked
    """
    def inner(self, version, request, disabled=False):
        content_object = version.content
        if is_registered_for_moderation(content_object):
            if is_obj_review_locked(content_object, request.user):
                disabled = True
        return func(self, version, request, disabled)
    return inner


def _get_archive_link(func):
    """
    Don't display archive link if the object is in moderation
    """
    def inner(self, version, request, disabled=False):
        content_object = version.content
        if is_registered_for_moderation(content_object):
            if get_active_moderation_request(content_object):
                disabled = True
        return func(self, version, request, disabled)
    return inner


def _is_placeholder_review_unlocked(placeholder, user):
    """
    Register review lock with placeholder checks framework to
    prevent users from editing content by directly accessing the URL
    """
    if is_registered_for_moderation(placeholder.source):
        if is_obj_review_locked(placeholder.source, user):
            return False
    return True


VersionAdmin.get_state_actions = get_state_actions(VersionAdmin.get_state_actions)
VersionAdmin._get_edit_link = _get_edit_link(VersionAdmin._get_edit_link)
VersionAdmin._get_archive_link = _get_archive_link(VersionAdmin._get_archive_link)
VersionAdmin._get_moderation_link = _get_moderation_link

fields.PlaceholderRelationField.default_checks += [_is_placeholder_review_unlocked]
