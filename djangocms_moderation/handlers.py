from __future__ import unicode_literals

from django.dispatch import receiver

from cms.operations import PUBLISH_PAGE_TRANSLATION
from cms.signals import post_obj_operation

from .constants import ACTION_FINISHED
from .helpers import get_active_moderation_request


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

    active_request = get_active_moderation_request(page, translation.language)

    if not active_request:
        return

    active_request.update_status(
        action=ACTION_FINISHED,
        by_user=request.user,
    )
