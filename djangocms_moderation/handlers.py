from __future__ import unicode_literals
import json

from django.dispatch import receiver

from cms.operations import PUBLISH_PAGE_TRANSLATION
from cms.signals import post_obj_operation

from .constants import ACTION_FINISHED
from .helpers import get_active_moderation_request, get_page_or_404
from .models import ConfirmationFormSubmission
from .signals import confirmation_form_submission


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


@receiver(confirmation_form_submission)
def moderation_confirmation_form_submission(sender, page, language, user, form_data, **kwargs):
    for field_data in form_data:
        if not set(('label', 'value')).issubset(field_data):
            raise ValueError('Each field dict should contain label and value keys.')

    active_request = get_active_moderation_request(page, language)
    next_step = active_request.user_get_step(user)

    ConfirmationFormSubmission.objects.create(
        request=active_request,
        for_step=next_step,
        by_user=user,
        data=json.dumps(form_data),
        confirmation_page=next_step.role.confirmation_page,
    )
