from django.shortcuts import get_object_or_404
from django.utils.translation import override as force_language

from cms.models import Page
from cms.utils.urlutils import admin_reverse

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


def get_admin_url(name, language, args):
    with force_language(language):
        return admin_reverse(name, args=args)


def get_current_moderation_request(page, language):
    try:
        return PageModerationRequest.objects.get(
            page=page,
            language=language,
            is_active=True
        )
    except PageModerationRequest.DoesNotExist:
        return None


def get_page(page_id, language):
    return get_object_or_404(
        Page,
        pk=page_id,
        is_page_type=False,
        publisher_is_draft=True,
        title_set__language=language,
    )
