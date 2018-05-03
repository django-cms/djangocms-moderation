from django.shortcuts import get_object_or_404

from cms.models import Page

from aldryn_forms.models import FormSubmission

from . import conf
from .models import (
    PageModeration,
    PageModerationRequest,
    PageModerationRequestActionFormSubmission,
    Workflow,
)


def get_default_workflow():
    try:
        workflow = Workflow.objects.get(is_default=True)
    except Workflow.DoesNotExist:
        workflow = None
    return workflow


def get_page_moderation_settings(page):
    moderation = PageModeration.objects.for_page(page)
    return moderation


def get_page_moderation_workflow(page):
    moderation = get_page_moderation_settings(page)

    if moderation:
        workflow = moderation.workflow
    else:
        workflow = get_default_workflow()
    return workflow


def get_workflow_or_none(pk):
    try:
        return Workflow.objects.get(pk=pk)
    except Workflow.DoesNotExist:
        return None


def get_active_moderation_request(page, language):
    try:
        return PageModerationRequest.objects.get(
            page=page,
            language=language,
            is_active=True,
        )
    except PageModerationRequest.DoesNotExist:
        return None


def get_page_or_404(page_id, language):
    return get_object_or_404(
        Page,
        pk=page_id,
        is_page_type=False,
        publisher_is_draft=True,
        title_set__language=language,
    )


def is_moderation_enabled(page):
    page_moderation_extension = get_page_moderation_settings(page)

    try:
        is_enabled = page_moderation_extension.enabled
    except AttributeError:
        is_enabled = True

    if conf.ENABLE_WORKFLOW_OVERRIDE:
        return is_enabled and Workflow.objects.exists()
    return is_enabled and bool(get_page_moderation_workflow(page))


def get_form_submission_or_none(pk):
    try:
        return FormSubmission.objects.get(pk=pk)
    except FormSubmission.DoesNotExist:
        return None


def get_action_form_for_step(active_request, step=None, user=None):
    try:
        if not step and not user:
            return None

        if step:
            current_step = step
        else:
            current_step = active_request.user_get_step(user)

        return PageModerationRequestActionFormSubmission.objects.get(
            request=active_request,
            for_step=current_step,
        )
    except PageModerationRequestActionFormSubmission.DoesNotExist:
        return None


def get_action_forms_for_request(active_request):
    try:
        return PageModerationRequestActionFormSubmission.objects.filter(
            request=active_request,
        )
    except PageModerationRequestActionFormSubmission.DoesNotExist:
        return None
