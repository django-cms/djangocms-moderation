from django.dispatch import receiver

from cms.operations import PUBLISH_PAGE_TRANSLATION
from cms.signals import post_obj_operation

from .constants import ACTION_FINISHED
from .helpers import get_page_moderation_workflow


@receiver(post_obj_operation)
def close_moderation_request(sender, **kwargs):
    request = kwargs['request']
    operation_type = kwargs['operation']
    is_publish = operation_type == PUBLISH_PAGE_TRANSLATION
    publish_successful = kwargs.get('successful')

    if not is_publish or not publish_successful:
        return

    page = kwargs['obj']
    translation = kwargs['translation']

    workflow = get_page_moderation_workflow(page)

    if not workflow:
        return

    active_request = workflow.get_active_request(page, translation.language)

    if not active_request:
        return

    active_request.update_status(
        action=ACTION_FINISHED,
        by_user=request.user,
    )
