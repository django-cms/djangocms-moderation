from threading import local


# thread local support
_thread_locals = local()


def set_current_language(user):
    _thread_locals.request_language = user
