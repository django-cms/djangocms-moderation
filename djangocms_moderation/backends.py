import uuid


def uuid4_backend(**kwargs):
    return uuid.uuid4().hex
