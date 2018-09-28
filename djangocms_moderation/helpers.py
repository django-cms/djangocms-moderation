from django.contrib.contenttypes.models import ContentType

from .models import ConfirmationFormSubmission, Workflow


def get_default_workflow():
    try:
        workflow = Workflow.objects.get(is_default=True)
    except Workflow.DoesNotExist:
        workflow = None
    return workflow


def get_moderation_workflow():
    # TODO for now just return default, this would need to depend on the collection
    # Might be as well not needed in 1.0.x, leaving it here for now
    return get_default_workflow()


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
        .filter(request=active_request, for_step=current_step)
    )
    return lookup.first()


def is_content_obj_version_unlocked(content_obj, user):
    """
    If djangocms_version_locking is installed, we need to consider it,
    otherwise, the content object is never version-locked for an user
    :param content_obj: <obj>
    :param user: <obj>
    :return: <bool>
    """
    try:
        from djangocms_version_locking.helpers import content_is_unlocked_for_user
    except ImportError:
        return True
    else:
        return content_is_unlocked_for_user(content_obj, user)
