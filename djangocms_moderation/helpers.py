from django.apps import apps
from django.contrib.contenttypes.models import ContentType
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext_lazy as _

from djangocms_versioning.models import Version

from .conf import COLLECTION_NAME_LENGTH_LIMIT
from .constants import COLLECTING
from .models import ConfirmationFormSubmission


try:
    from djangocms_version_locking.helpers import content_is_unlocked_for_user
except ImportError:
    content_is_unlocked_for_user = None


def get_page_or_404(obj_id, language):
    content_type = ContentType.objects.get(app_label="cms", model="page")  # how do we get this

    return content_type.get_object_for_this_type(
        pk=obj_id,
        is_page_type=False,
        pagecontent_set__language=language,
    )


def get_form_submission_for_step(active_request, current_step):
    lookup = (
        ConfirmationFormSubmission
        .objects
        .filter(moderation_request=active_request, for_step=current_step)
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
    moderation_config = apps.get_app_config('djangocms_moderation')
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
    if name_length_limit and len(collection_name) > name_length_limit:
        collection_name = "{}{}".format(
            collection_name[:name_length_limit],
            '...',
        )

    if moderation_request.collection.status == COLLECTING:
        button_title = _('In collection "%(collection_name)s (%(collection_id)s)"') % {
            'collection_name': collection_name,
            'collection_id': moderation_request.collection.id
        }
    else:
        button_title = _('In moderation "%(collection_name)s (%(collection_id)s)"') % {
            'collection_name': collection_name,
            'collection_id': moderation_request.collection.id
        }
    url = "{}?collection__id__exact={}".format(
        reverse('admin:djangocms_moderation_moderationrequest_changelist'),
        moderation_request.collection.id
    )
    return button_title, url
