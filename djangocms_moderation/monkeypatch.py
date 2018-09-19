from cms.utils.urlutils import add_url_parameters
from django.utils.html import format_html
from djangocms_versioning.admin import VersionAdmin
from django.utils.translation import ugettext_lazy as _
from djangocms_versioning.constants import DRAFT

from djangocms_moderation.utils import (
    get_admin_url,
    is_obj_review_locked,
    get_active_moderation_request,
)


def get_state_actions(func):
    """
    Monkey patch VersionAdmin's get_state_actions to remove publish link,
    as we don't want publishing in moderation.
    Add moderation link
    """
    def inner(self):
        links = func(self)
        links = [link for link in links if link != self._get_publish_link]
        return links + [self._get_moderation_link]
    return inner


def _get_moderation_link(self, version, request):
    if not version.state == DRAFT:
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
        if is_obj_review_locked(version.content, request.user):
            return ''
        return func(self, version, request)

    return inner


VersionAdmin.get_state_actions = get_state_actions(VersionAdmin.get_state_actions)
VersionAdmin._get_edit_link = _get_edit_link(VersionAdmin._get_edit_link)
VersionAdmin._get_moderation_link = _get_moderation_link
