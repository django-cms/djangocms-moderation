from threading import local


# thread local support
_thread_locals = local()


def set_current_language(current_language):
    _thread_locals.request_language = current_language
