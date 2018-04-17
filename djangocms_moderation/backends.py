import uuid


def default_workflow_reference_number_backend(moderation_request, **kwargs):
    return uuid.uuid4()
