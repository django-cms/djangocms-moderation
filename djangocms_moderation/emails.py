from __future__ import unicode_literals

from django.conf import settings
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.utils.encoding import force_text
from django.utils.translation import ugettext_lazy as _

from .utils import get_absolute_url


from . import constants  # isort:skip


try:
    from django.urls import reverse
except ImportError:
    from django.core.urlresolvers import reverse


email_subjects = {
    constants.ACTION_APPROVED: _('Approved moderation requests'),
    constants.ACTION_REJECTED: _('Rejected moderation requests'),
    constants.ACTION_CANCELLED: _('Request for moderation deleted'),
}


def _send_email(
    collection,
    moderation_requests,
    recipients,
    subject,
    template,
    by_user
):
    admin_url = reverse('admin:djangocms_moderation_moderationrequest_changelist')
    admin_url = "{}?collection__id__exact={}".format(
        admin_url,
        collection.id
    )

    context = {
        'collection': collection,
        'moderation_requests': moderation_requests,
        'author_name': collection.author_name,
        'admin_url': get_absolute_url(admin_url),
        'job_id': collection.job_id,
        'by_user': by_user,
    }
    template = 'djangocms_moderation/emails/moderation-request/{}'.format(template)

    # TODO What language should the email be sent in? e.g. `with force_language(lang):`
    subject = force_text(subject)
    content = render_to_string(template, context)

    message = EmailMessage(
        subject=subject,
        body=content,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=recipients,
    )
    return message.send()


def notify_collection_author(collection, moderation_requests, action, by_user):
    if action not in email_subjects or not collection.author.email:
        return

    status = _send_email(
        collection=collection,
        moderation_requests=moderation_requests,
        recipients=[collection.author.email],
        subject=email_subjects[action],
        template='{}.txt'.format(action),
        by_user=by_user,
    )
    return status


def notify_collection_moderators(collection, moderation_requests, action_obj):
    if action_obj.to_user_id and not action_obj.to_user.email:
        return 0
    try:
        recipients = [action_obj.to_user.email]
    except AttributeError:
        users = action_obj.to_role.get_users_queryset().exclude(email='')
        recipients = users.values_list('email', flat=True)

    if not recipients:
        return 0

    status = _send_email(
        collection=collection,
        moderation_requests=moderation_requests,
        recipients=recipients,
        subject=_('Review requested'),
        template='request.txt',
        by_user=action_obj.by_user
    )
    return status
