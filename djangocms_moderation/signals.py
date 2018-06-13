import django.dispatch

confirmation_form_submission = django.dispatch.Signal(
    providing_args=['page_id', 'language', 'user', 'form_data']
)
