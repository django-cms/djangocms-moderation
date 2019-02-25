from django.db import models
from django.urls import reverse

from cms.models import CMSPlugin
from cms.models.fields import PlaceholderField


class Poll(models.Model):
    name = models.TextField()

    def __str__(self):
        return "{} ({})".format(self.name, self.pk)


class PollContent(models.Model):
    poll = models.ForeignKey(Poll, on_delete=models.CASCADE)
    language = models.TextField()
    text = models.TextField()
    placeholder = PlaceholderField("placeholder")

    def __str__(self):
        return self.text

    def get_absolute_url(self):
        return reverse("admin:polls_pollcontent_changelist")

    def get_placeholders(self):
        return [self.placeholder]


class Answer(models.Model):
    poll_content = models.ForeignKey(PollContent, on_delete=models.CASCADE)
    text = models.TextField()

    def __str__(self):
        return self.text


class PollPlugin(CMSPlugin):
    cmsplugin_ptr = models.OneToOneField(
        CMSPlugin,
        on_delete=models.CASCADE,
        related_name="%(app_label)s_%(class)s",
        parent_link=True,
    )

    poll = models.ForeignKey(Poll, on_delete=models.CASCADE)

    def __str__(self):
        return str(self.poll)
