from django.db import models
from django.urls import reverse
from django.utils.functional import cached_property

from cms.models import CMSPlugin
from cms.models.fields import PlaceholderRelationField
from cms.utils.placeholder import get_placeholder_from_slot


class NoneModeratedPoll(models.Model):
    name = models.TextField()

    def __str__(self):
        return f"{self.name} ({self.pk})"


class NoneModeratedPollContent(models.Model):
    poll = models.ForeignKey(NoneModeratedPoll, on_delete=models.CASCADE)
    language = models.TextField()
    text = models.TextField()
    placeholders = PlaceholderRelationField()

    @cached_property
    def placeholder(self):
        return get_placeholder_from_slot(self.placeholders, "placeholder")

    def __str__(self):
        return self.text

    def get_absolute_url(self):
        return reverse("admin:nonemoderatedpoll_nonemoderatedpollcontent_changelist")

    def get_placeholders(self):
        return [self.placeholder]


class NoneModeratedPollPlugin(CMSPlugin):
    cmsplugin_ptr = models.OneToOneField(
        CMSPlugin,
        on_delete=models.CASCADE,
        related_name="%(app_label)s_%(class)s",
        parent_link=True,
    )

    poll = models.ForeignKey(NoneModeratedPoll, on_delete=models.CASCADE)

    def __str__(self):
        return str(self.poll)
