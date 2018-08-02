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
    constants.ACTION_APPROVED: _('Changes Approved'),
    constants.ACTION_CANCELLED: _('Request for moderation cancelled'),
    constants.ACTION_REJECTED: _('Changes Rejected'),
}


def _send_email(collection, action, recipients, subject, template):
    if action.to_user_id:
        moderator_name = action.get_to_user_name()
    elif action.to_role_id:
        moderator_name = action.to_role.name
    else:
        moderator_name = ''

    admin_url = reverse('admin:djangocms_moderation_moderationcollection_change', args=(collection.pk,))
    context = {
        'collection': collection,
        'author_name': collection.author_name,
        'by_user_name': action.get_by_user_name(),
        'moderator_name': moderator_name,
        'admin_url': get_absolute_url(admin_url),
    }
    template = 'djangocms_moderation/emails/moderation-request/{}'.format(template)

    # TODO consider cms's `with force_language(lang)`?
    subject = force_text(subject)
    content = render_to_string(template, context)

    message = EmailMessage(
        subject=subject,
        body=content,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=recipients,
    )
    return message.send()


def notify_request_author(request, action):
    if action.action not in email_subjects:
        # TODO: FINISH THIS
        return 0

    if not request.author.email:
        return 0

    status = _send_email(
        request=request,
        action=action,
        recipients=[request.author.email],
        subject=email_subjects[action.action],
        template='{}.txt'.format(action.action),
    )
    return status


def notify_collection_moderators(collection, action):
    if action.to_user_id and not action.to_user.email:
        return 0

    try:
        recipients = [action.to_user.email]
    except AttributeError:
        users = action.to_role.get_users_queryset().exclude(email='')
        recipients = users.values_list('email', flat=True)

    if not recipients:
        return 0

    status = _send_email(
        collection=collection,
        action=action,
        recipients=recipients,
        subject=_('Review requested'),
        template='request.txt',
    )
    return status
