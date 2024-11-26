from django.apps import apps
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.db.models import Q
from django.template.defaultfilters import truncatechars
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from cms.models import CMSPlugin
from cms.utils.plugins import downcast_plugins

from djangocms_versioning import versionables
from djangocms_versioning.constants import DRAFT
from djangocms_versioning.models import Version

from .conf import COLLECTION_NAME_LENGTH_LIMIT
from .constants import COLLECTING
from .models import ConfirmationFormSubmission


User = get_user_model()

try:
    from djangocms_versioning.helpers import content_is_unlocked_for_user
except ImportError:
    try:
        # Before djangocms-versioning 2.0.0, version locking was in a separate package
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
    from djangocms_moderation.models import ModerationRequest

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
    url = "{}?moderation_request__collection__id={}".format(
        reverse('admin:djangocms_moderation_moderationrequest_changelist'),
        moderation_request.collection_id
    )
    return button_title, url


def get_all_reviewers():
    return User.objects.filter(
        Q(groups__role__workflowstep__workflow__moderation_collections__isnull=False)
        | Q(role__workflowstep__workflow__moderation_collections__isnull=False)
    ).distinct()


def get_all_moderators():
    return User.objects.filter(moderationcollection__author__isnull=False).distinct()


def _get_moderatable_version(versionable, grouper, parent_version_filters):
    """
    Private helper to get a specific version from a field instance
    """
    # If the content model is not registered with moderation nothing should be returned
    if not is_registered_for_moderation(versionable.content_model()):
        return

    filters = {versionable.grouper_field_name: grouper}
    if (
        "language" in versionable.extra_grouping_fields
        and "language" in parent_version_filters
    ):
        filters["language"] = parent_version_filters["language"]
    try:
        return Version.objects.filter_by_grouping_values(versionable, **filters).get(
            state=DRAFT
        )
    except Version.DoesNotExist:
        return


def _get_nested_moderated_children_from_placeholder_plugin(instance, placeholder, parent_version_filters):
    """
    Find all nested versionable objects, traverses through all attached models until it finds
    any models that are versioned.
    """
    # Catch Many to many fields that don't have _meta
    # FIXME: Handle nested M2M instances
    if not hasattr(instance, "_meta"):
        return

    for field in instance._meta.get_fields():
        if not field.is_relation or field.auto_created:
            continue

        candidate = getattr(instance, field.name)

        # Break early if the field is None, a placeholder, or is a CMSPlugin instance
        # We do this to save unnecessary processing
        if not candidate or candidate == placeholder or isinstance(candidate, CMSPlugin):
            continue

        try:
            versionable = versionables.for_grouper(candidate)
        except KeyError:
            yield from _get_nested_moderated_children_from_placeholder_plugin(
                candidate, placeholder, parent_version_filters
            )
            continue

        version = _get_moderatable_version(
            versionable, candidate, parent_version_filters
        )
        if version:
            yield version


def get_moderated_children_from_placeholder(placeholder, parent_version_filters):
    """
    Get all moderated children version objects from a placeholder
    """
    for plugin in downcast_plugins(placeholder.get_plugins()):
        yield from _get_nested_moderated_children_from_placeholder_plugin(plugin, placeholder, parent_version_filters)
