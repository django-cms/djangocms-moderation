import django.dispatch


confirmation_form_submission = django.dispatch.Signal(
    providing_args=["page", "language", "user", "form_data"]
)

submitted_for_review = django.dispatch.Signal(
    providing_args=[
        "collection",
        "moderation_requests",
        "user",
        "rework",
        "workflow"
    ]
)

published = django.dispatch.Signal(
    providing_args=[
        "collection",
        "moderator",
        "moderation_requests",
        "workflow"
    ]
)

unpublished = django.dispatch.Signal(
    providing_args=[
        "collection",
        "moderator",
        "moderation_requests",
        "workflow"
    ]
)
