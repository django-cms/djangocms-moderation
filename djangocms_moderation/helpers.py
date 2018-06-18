from django.shortcuts import get_object_or_404

from cms.models import Page

from . import conf
from .models import (
    ConfirmationFormSubmission,
    PageModeration,
    PageModerationRequest,
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


def get_form_submission_for_step(active_request, current_step):
    lookup = (
        ConfirmationFormSubmission
        .objects
        .filter(request=active_request, for_step=current_step)
    )
    return lookup.first()
