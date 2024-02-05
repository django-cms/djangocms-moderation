import uuid


def uuid4_backend(**kwargs):
    return uuid.uuid4().hex


def sequential_number_backend(**kwargs):
    """
    This backed uses moderation request's primary key to a produce readable
    semi-sequential numbers.
    """
    moderation_request = kwargs["moderation_request"]
    return str(moderation_request.pk)


def sequential_number_with_identifier_prefix_backend(**kwargs):
    """
    This backed uses moderation request's primary key to a produce readable
    semi-sequential numbers, prefixed with `workflow.identifier` field, if set
    """
    moderation_request = kwargs["moderation_request"]
    return f"{moderation_request.workflow.identifier}{moderation_request.pk}"
