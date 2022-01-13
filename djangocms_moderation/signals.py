import django.dispatch


confirmation_form_submission = django.dispatch.Signal()

submitted_for_review = django.dispatch.Signal()

published = django.dispatch.Signal()
