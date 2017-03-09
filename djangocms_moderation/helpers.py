from .models import PageModeration, Workflow


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
