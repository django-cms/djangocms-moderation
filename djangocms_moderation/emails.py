import enum

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.encoding import force_str
from django.utils.translation import gettext_lazy as _

from .conf import EMAIL_NOTIFICATIONS_FAIL_SILENTLY
from .utils import get_absolute_url


from . import constants  # isort:skip


@enum.unique
class EmailNotificationType(enum.Enum):
    APPROVED = constants.ACTION_APPROVED
    CANCELLED = constants.ACTION_CANCELLED
    REJECTED = constants.ACTION_REJECTED
    REQUEST = "request"


@enum.unique
class EmailNotificationFormat(enum.Enum):
    PLAIN = "txt"
    HTML = "html"


email_subjects = {
    constants.ACTION_APPROVED: _("Approved moderation requests"),
    constants.ACTION_REJECTED: _("Rejected moderation requests"),
    constants.ACTION_CANCELLED: _("Request for moderation deleted"),
}


def _format_admin_url(collection) -> str:
    admin_url = "{}?moderation_request__collection__id={}".format(
        reverse("admin:djangocms_moderation_moderationrequest_changelist"),
        collection.id,
    )
    return get_absolute_url(admin_url)


def _render_email(
    collection,
    moderation_requests,
    notification_type: EmailNotificationType,
    by_user,
    notification_format: EmailNotificationFormat,
) -> str:
    base_dir = "djangocms_moderation/emails/moderation-request/"
    filename = f"{notification_type.value}.{notification_format.value}"

    return render_to_string(
        f"{base_dir}/{filename}",
        context={
            "collection": collection,
            "moderation_requests": moderation_requests,
            "author_name": collection.author_name,
            "admin_url": _format_admin_url(collection),
            "job_id": collection.job_id,
            "by_user": by_user,
        }
    )


def _send_email(
    collection,
    moderation_requests,
    recipients,
    subject,
    notification_type: EmailNotificationType,
    by_user,
):
    text_content = _render_email(
        collection,
        moderation_requests,
        notification_type,
        by_user,
        EmailNotificationFormat.PLAIN,
    )
    html_content = _render_email(
        collection,
        moderation_requests,
        notification_type,
        by_user,
        EmailNotificationFormat.HTML,
    )

    message = EmailMultiAlternatives(
        subject=force_str(subject),
        body=text_content,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=recipients,
    )
    message.attach_alternative(html_content, "text/html")
    return message.send(
        fail_silently=EMAIL_NOTIFICATIONS_FAIL_SILENTLY
    )


def notify_collection_author(
    collection, moderation_requests, action: str, by_user
):
    if action not in email_subjects or not collection.author.email:
        return

    status = _send_email(
        collection=collection,
        moderation_requests=moderation_requests,
        recipients=[collection.author.email],
        subject=email_subjects[action],
        notification_type=EmailNotificationType(action),
        by_user=by_user,
    )
    return status


def notify_collection_moderators(collection, moderation_requests, action_obj):
    if action_obj.to_user_id and not action_obj.to_user.email:
        return 0
    try:
        recipients = [action_obj.to_user.email]
    except AttributeError:
        users = action_obj.to_role.get_users_queryset().exclude(email="")
        recipients = users.values_list("email", flat=True)

    if not recipients:
        return 0

    status = _send_email(
        collection=collection,
        moderation_requests=moderation_requests,
        recipients=recipients,
        subject=_("Review requested"),
        notification_type=EmailNotificationType.REQUEST,
        by_user=action_obj.by_user,
    )
    return status
