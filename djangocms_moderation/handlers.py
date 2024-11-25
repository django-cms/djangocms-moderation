import json

from django.dispatch import receiver

from .models import ConfirmationFormSubmission
from .signals import confirmation_form_submission


@receiver(confirmation_form_submission)
def moderation_confirmation_form_submission(
    sender, page, language, user, form_data, **kwargs
):
    for field_data in form_data:
        if not {"label", "value"}.issubset(field_data):
            raise ValueError("Each field dict should contain label and value keys.")

    # TODO Confirmation pages are not used/working in 1.0.x yet
    active_request = None  # get_active_moderation_request(page, language)
    if active_request:
        next_step = active_request.user_get_step(user)

        ConfirmationFormSubmission.objects.create(
            request=active_request,
            for_step=next_step,
            by_user=user,
            data=json.dumps(form_data),
            confirmation_page=next_step.role.confirmation_page,
        )
