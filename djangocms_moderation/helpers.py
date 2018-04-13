from django.shortcuts import get_object_or_404

from cms.models import Page

from .models import PageModeration, Workflow, PageModerationRequest


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


def get_workflow_by_id(pk):
    try:
        return Workflow.objects.get(pk=pk)
    except Workflow.DoesNotExist:
        return None


def get_current_moderation_request(page, language):
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


def can_page_be_moderated(page):
    page_moderation_extension = getattr(page, 'pagemoderation', None)
    if page_moderation_extension and page_moderation_extension.disable_moderation:
        return False
    return True
