from django.utils.html import format_html
from django.utils.translation import ugettext_lazy as _

from cms.utils.urlutils import add_url_parameters

from djangocms_versioning.admin import VersionAdmin
from djangocms_versioning.constants import DRAFT

from .utils import (
    get_active_moderation_request,
    get_admin_url,
    is_obj_review_locked,
)
from .helpers import is_registered_for_moderation


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
    moderation_request = get_active_moderation_request(version.content)
    if moderation_request:
        return _('In Moderation "%(collection_name)s"') % {
            'collection_name': moderation_request.collection.name
        }
    else:
        url = add_url_parameters(
            get_admin_url(
                name='cms_moderation_item_to_collection',
                language='en',
                args=()
            ),
            version_id=version.pk
        )
        # TODO use a fancy icon as for the rest of the actions?
        return format_html(
            '<a href="{}">{}</a>',
            url,
            _('Submit for moderation')
        )


def _get_edit_link(func):
    """
    Don't display edit link if the object is review locked
    """
    def inner(self, version, request):
        if is_registered_for_moderation(version.content):
            if is_obj_review_locked(version.content, request.user):
                return ''
        return func(self, version, request)

    return inner


VersionAdmin.get_state_actions = get_state_actions(VersionAdmin.get_state_actions)
VersionAdmin._get_edit_link = _get_edit_link(VersionAdmin._get_edit_link)
VersionAdmin._get_moderation_link = _get_moderation_link
