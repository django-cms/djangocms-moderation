import uuid


def uuid4_backend(**kwargs):
    return uuid.uuid4().hex


def sequential_number_backend(**kwargs):
    """
    This backed uses moderation request's primary key to produce readable
    semi-sequential numbers.
    """
    moderation_request = kwargs['moderation_request']
    return str(moderation_request.pk)
