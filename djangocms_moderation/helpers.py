from django.shortcuts import get_object_or_404
from django.contrib.contenttypes.models import ContentType

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
    content_type = ContentType.objects.get_for_model(page)
    try:
        page = PageModerationRequest.objects.get(
            content_type=content_type,
            # content_object=page,
            object_id=page.pk,
            language=language,
            is_active=True,
        )
        # import pdb; pdb.set_trace()
        return page
    except PageModerationRequest.DoesNotExist:
        # import pdb; pdb.set_trace()
        return None


def get_page_or_404(page_id, language):
   content_type = ContentType.objects.get(app_label="cms", model="page") # how do we get this
   return content_type.get_object_for_this_type(
        pk=page_id,
        is_page_type=False, # get these lines from app registration 
        publisher_is_draft=True, # something like moderated_object_kwargs
        title_set__language=language
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
