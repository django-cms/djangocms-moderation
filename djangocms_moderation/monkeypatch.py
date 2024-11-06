from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from cms.models import fields
from cms.utils.urlutils import add_url_parameters

from djangocms_versioning import admin, models
from djangocms_versioning.constants import DRAFT
from djangocms_versioning.exceptions import ConditionFailed
from djangocms_versioning.helpers import version_list_url
from djangocms_versioning.models import Version

from djangocms_moderation.helpers import (
    get_active_moderation_request,
    get_moderation_button_title_and_url,
    is_obj_review_locked,
    is_obj_version_unlocked,
    is_registered_for_moderation,
)
from djangocms_moderation.utils import get_admin_url


def get_state_actions(func):
    """
    Monkey patch VersionAdmin's get_state_actions to add Add moderation link
    """

    def inner(self):
        links = func(self)
        return links + [self._get_moderation_link]

    return inner


def _get_moderation_link(self, version, request):
    if not is_registered_for_moderation(version.content):
        return ""

    if version.state != DRAFT:
        return ""

    content_object = version.content
    moderation_request = get_active_moderation_request(content_object)
    if moderation_request:
        title, url = get_moderation_button_title_and_url(moderation_request)
        return format_html('<a href="{}">{}</a>', url, title)
    elif is_obj_version_unlocked(content_object, request.user):
        url = add_url_parameters(
            get_admin_url(
                name="cms_moderation_items_to_collection", language="en", args=()
            ),
            version_ids=version.pk,
            return_to_url=version_list_url(version.content),
        )
        # TODO use a fancy icon as for the rest of the actions?
        return format_html('<a href="{}">{}</a>', url, _("Submit for moderation"))
    return ""


def _is_placeholder_review_unlocked(placeholder, user):
    """
    Register review lock with placeholder checks framework to
    prevent users from editing content by directly accessing the URL
    """
    if is_registered_for_moderation(placeholder.source):
        if is_obj_review_locked(placeholder.source, user):
            return False
    return True


def _is_version_review_locked(message):
    """
    Checks if version is in review
    """
    def inner(version, user):
        if is_registered_for_moderation(version.content) and is_obj_review_locked(
            version.content, user
        ):
            raise ConditionFailed(message)

    return inner


def get_latest_draft_version(version):
    """Get latest draft version of version object
    """
    drafts = Version.objects.filter_by_content_grouping_values(version.content).filter(
        state=DRAFT
    )
    return drafts.first()


def _is_draft_version_review_locked(message):
    def inner(version, user):
        """
        Checks if version is a draft and in review
        """
        draft_version = get_latest_draft_version(version)
        if (
            draft_version
            and is_registered_for_moderation(draft_version.content)
            and is_obj_review_locked(draft_version.content, user)
        ):
            raise ConditionFailed(message)

    return inner


def _get_publish_link(func):
    """
    Monkey patch VersionAdmin's _get_publish_link to remove publish link,
    if obj.content is registered with moderation
    """

    def inner(self, obj, request):
        if is_registered_for_moderation(obj.content):
            return ""
        return func(self, obj, request)

    return inner


def _check_registered_for_moderation(message):
    """
    Fail check if object is registered for moderation
    """
    def inner(version, user):
        if is_registered_for_moderation(version.content):
            raise ConditionFailed(message)

    return inner


admin.VersionAdmin._get_publish_link = _get_publish_link(
    admin.VersionAdmin._get_publish_link
)

admin.VersionAdmin.get_state_actions = get_state_actions(
    admin.VersionAdmin.get_state_actions
)
admin.VersionAdmin._get_moderation_link = _get_moderation_link

models.Version.check_archive += [
    _is_version_review_locked(
        _("Cannot archive a version in an active moderation collection")
    )
]
models.Version.check_revert += [
    _is_draft_version_review_locked(
        _("Cannot revert when draft version is in an active moderation collection")
    )
]
models.Version.check_discard += [
    _is_version_review_locked(
        _("Cannot archive a version in an active moderation collection")
    )
]
models.Version.check_modify += [
    _is_version_review_locked(_("Version is in an active moderation collection"))
]
models.Version.check_edit_redirect += [
    _is_version_review_locked(
        _("Cannot edit a version in an active moderation collection")
    )
]
models.Version.check_publish += [
    _check_registered_for_moderation(_("Content cannot be published directly. Use the moderation process."))
]

fields.PlaceholderRelationField.default_checks += [_is_placeholder_review_unlocked]
