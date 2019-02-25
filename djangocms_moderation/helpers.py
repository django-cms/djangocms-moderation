from django.apps import apps
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.core.urlresolvers import reverse
from django.db.models import Q
from django.template.defaultfilters import truncatechars
from django.utils.translation import ugettext_lazy as _

from cms.utils.plugins import downcast_plugins

from djangocms_versioning import versionables
from djangocms_versioning.constants import DRAFT
from djangocms_versioning.models import Version

from .conf import COLLECTION_NAME_LENGTH_LIMIT
from .constants import COLLECTING
from .models import ConfirmationFormSubmission


User = get_user_model()

try:
    from djangocms_version_locking.helpers import content_is_unlocked_for_user
except ImportError:
    content_is_unlocked_for_user = None


def get_page_or_404(obj_id, language):
    content_type = ContentType.objects.get(
        app_label="cms", model="page"
    )  # how do we get this

    return content_type.get_object_for_this_type(
        pk=obj_id, is_page_type=False, pagecontent_set__language=language
    )


def get_form_submission_for_step(active_request, current_step):
    lookup = ConfirmationFormSubmission.objects.filter(
        moderation_request=active_request, for_step=current_step
    )
    return lookup.first()


def is_obj_version_unlocked(content_obj, user):
    """
    If djangocms_version_locking is installed, we need to consider it,
    otherwise, the content object is never version-locked for an user
    :param content_obj: <obj>
    :param user: <obj>
    :return: <bool>
    """
    if content_is_unlocked_for_user is not None:
        return content_is_unlocked_for_user(content_obj, user)
    return True


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
    return not moderation_request.user_can_resubmit(user)


def get_active_moderation_request(content_object):
    """
    If this returns None, it means there is no active_moderation request for this
    object, and it means it can be submitted for new moderation
    """
    from djangocms_moderation.models import ModerationRequest  # noqa

    version = Version.objects.get_for_content(content_object)

    try:
        return ModerationRequest.objects.get(version=version, is_active=True)
    except ModerationRequest.DoesNotExist:
        return None


def is_registered_for_moderation(content_object):
    """
    Helper method to check if model is registered to moderated
    @param content_object: content object
    @return: bool
    """
    moderation_config = apps.get_app_config("djangocms_moderation")
    moderated_models = moderation_config.cms_extension.moderated_models
    return content_object.__class__ in moderated_models


def get_moderation_button_title_and_url(moderation_request):
    """
    Helper to get the moderation button title and url for an
    existing active moderation request
    :param moderation_request: <obj>
    :return: title: <str>, url: <str>
    """
    name_length_limit = COLLECTION_NAME_LENGTH_LIMIT
    collection_name = moderation_request.collection.name
    if name_length_limit:
        collection_name = truncatechars(collection_name, name_length_limit)

    if moderation_request.collection.status == COLLECTING:
        button_title = _('In collection "%(collection_name)s (%(collection_id)s)"') % {
            "collection_name": collection_name,
            "collection_id": moderation_request.collection_id,
        }
    else:
        button_title = _('In moderation "%(collection_name)s (%(collection_id)s)"') % {
            "collection_name": collection_name,
            "collection_id": moderation_request.collection_id,
        }
    url = "{}?collection__id__exact={}".format(
        reverse("admin:djangocms_moderation_moderationrequest_changelist"),
        moderation_request.collection_id,
    )
    return button_title, url


def get_all_reviewers():
    return User.objects.filter(
        Q(groups__role__workflowstep__workflow__moderation_collections__isnull=False)
        | Q(role__workflowstep__workflow__moderation_collections__isnull=False)
    ).distinct()


def get_all_moderators():
    return User.objects.filter(moderationcollection__author__isnull=False).distinct()


def _get_moderatable_version(versionable, field_instance, language):
    """
    Private helper to get a specific version from a field instance
    """
    # If the content model is not registered with moderation nothing should be returned
    if (
        versionable.content_model
        not in apps.get_app_config(
            "djangocms_moderation"
        ).cms_extension.moderated_models
    ):
        return

    filters = {versionable.grouper_field_name: field_instance}
    if language is not None and "language" in versionable.extra_grouping_fields:
        filters["language"] = language
    # Get the draft version if it exists using grouping values
    return Version.objects.filter_by_grouping_values(versionable, **filters).get(
        state=DRAFT
    )


def get_moderated_children_from_placeholder(placeholder, language=None):
    """
    Get all moderated children version objects from a placeholder
    """
    moderatable_child_list = []

    for plugin in downcast_plugins(placeholder.get_plugins()):

        plugin_model = plugin.get_plugin_class().model._meta
        field_list = [
            f for f in plugin_model.get_fields() if f.is_relation and not f.auto_created
        ]

        for field in field_list:
            field_instance = getattr(plugin, field.name)
            # Skip fields that are not versionable because field_list contains many unrelated fields
            try:
                versionable = versionables.for_grouper(field_instance)
            except KeyError:
                continue
            version = _get_moderatable_version(versionable, field_instance, language)
            if version:
                moderatable_child_list.append(version)

    return moderatable_child_list
