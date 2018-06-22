from __future__ import unicode_literals

from django.conf import settings
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.utils.encoding import force_text
from django.utils.translation import override as force_language, ugettext_lazy as _

try:
    from django.urls import reverse
except ImportError:
    from django.core.urlresolvers import reverse

from cms.utils.conf import get_cms_setting

from . import constants
from .utils import get_absolute_url


email_subjects = {
    constants.ACTION_APPROVED: _('Changes Approved'),
    constants.ACTION_CANCELLED: _('Request for moderation cancelled'),
    constants.ACTION_REJECTED: _('Changes Rejected'),
}


def _send_email(request, action, recipients, subject, template):
    page = request.page
    edit_on = get_cms_setting('CMS_TOOLBAR_URL__EDIT_ON')
    page_url = page.get_absolute_url(request.language) + '?' + edit_on
    author_name = request.get_first_action().get_by_user_name()

    if action.to_user_id:
        moderator_name = action.get_to_user_name()
    elif action.to_role_id:
        moderator_name = action.to_role.name
    else:
        moderator_name = ''

    site = page.node.site
    admin_url = reverse('admin:djangocms_moderation_pagemoderationrequest_change', args=(request.pk, ))
    context = {
        'page': page,
        'page_url': get_absolute_url(page_url, site),
        'author_name': author_name,
        'by_user_name': action.get_by_user_name(),
        'moderator_name': moderator_name,
        'job_number': request.reference_number,
        'comment': request.get_last_action().message,
        'admin_url': get_absolute_url(admin_url, site),
    }
    template = 'djangocms_moderation/emails/moderation-request/{}'.format(template)

    with force_language(request.language):
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

    author = request.get_first_action().by_user

    if not author.email:
        return 0

    status = _send_email(
        request=request,
        action=action,
        recipients=[author.email],
        subject=email_subjects[action.action],
        template='{}.txt'.format(action.action),
    )
    return status


def notify_requested_moderator(request, action):
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
        request=request,
        action=action,
        recipients=recipients,
        subject=_('Review requested'),
        template='request.txt',
    )
    return status
