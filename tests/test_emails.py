import itertools
import os

from django.core import mail
from django.urls import reverse

from djangocms_moderation import constants
from djangocms_moderation.emails import (
    EmailNotificationFormat,
    EmailNotificationType,
    notify_collection_author,
)
from djangocms_moderation.utils import get_absolute_url
from tests.utils.base import BaseTestCase


class EmailNotificationTestCase(BaseTestCase):
    def test_each_required_email_template_exists(self):
        for notification_type, notification_format in itertools.product(
            EmailNotificationType, EmailNotificationFormat
        ):
            filename = f"{notification_type.value}.{notification_format.value}"
            path = (
                "djangocms_moderation/templates/"
                + "djangocms_moderation/emails/moderation-request/"
                + filename
            )
            with self.subTest(filename):
                self.assertTrue(
                    os.path.exists(path),
                    f"missing moderation request email template {filename}",
                )

    def test_admin_url_points_to_working_changelist(self):
        notify_collection_author(
            collection=self.collection1,
            moderation_requests=[self.moderation_request1],
            action=constants.ACTION_APPROVED,
            by_user=self.user2,
        )

        self.assertEqual(len(mail.outbox), 1)
        admin_url = "{}?moderation_request__collection__id={}".format(
            reverse("admin:djangocms_moderation_moderationrequest_changelist"),
            self.collection1.pk,
        )
        self.assertIn(get_absolute_url(admin_url), mail.outbox[0].body)

        # The link in the email must resolve to the collection's request list
        with self.login_user_context(self.user):
            response = self.client.get(admin_url)
        self.assertEqual(response.status_code, 200)
