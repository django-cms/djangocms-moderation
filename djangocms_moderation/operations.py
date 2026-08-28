from contextlib import contextmanager
from contextvars import ContextVar


_moderated_unpublish = ContextVar("djangocms_moderation_moderated_unpublish", default=False)


@contextmanager
def moderated_unpublish():
    """Mark an unpublish operation as the final step of moderation."""
    token = _moderated_unpublish.set(True)
    try:
        yield
    finally:
        _moderated_unpublish.reset(token)


def is_moderated_unpublish():
    return _moderated_unpublish.get()
