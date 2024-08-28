from django.db import models
from django.urls import reverse
from django.utils.functional import cached_property

from cms.models import CMSPlugin, Placeholder
from cms.models.fields import PlaceholderRelationField


class Poll(models.Model):
    name = models.TextField()

    def __str__(self):
        return f"{self.name} ({self.pk})"


class PollContent(models.Model):
    poll = models.ForeignKey(Poll, on_delete=models.CASCADE)
    language = models.TextField()
    text = models.TextField()
    placeholders = PlaceholderRelationField()

    @cached_property
    def placeholder(self):
        try:
            return self.placeholders.get(slot='content')
        except Placeholder.DoesNotExist:
            from cms.utils.placeholder import rescan_placeholders_for_obj
            rescan_placeholders_for_obj(self)
            return self.placeholders.get(slot='content')

    def __str__(self):
        return self.text

    def get_absolute_url(self):
        return reverse("admin:polls_pollcontent_changelist")

    def get_placeholders(self):
        return [self.placeholder]

    def get_template(self):
        return 'polls/poll_content.html'


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


class NestedPoll(models.Model):
    poll = models.ForeignKey(Poll, on_delete=models.CASCADE)

    def __str__(self):
        return self.poll


class NestedPollPlugin(CMSPlugin):
    cmsplugin_ptr = models.OneToOneField(
        CMSPlugin,
        on_delete=models.CASCADE,
        related_name="%(app_label)s_%(class)s",
        parent_link=True,
    )

    nested_poll = models.ForeignKey(NestedPoll, on_delete=models.CASCADE)

    def __str__(self):
        return str(self.nested_poll)


class DeeplyNestedPoll(models.Model):
    nested_poll = models.ForeignKey(NestedPoll, on_delete=models.CASCADE)

    def __str__(self):
        return self.nested_poll


class DeeplyNestedPollPlugin(CMSPlugin):
    cmsplugin_ptr = models.OneToOneField(
        CMSPlugin,
        on_delete=models.CASCADE,
        related_name="%(app_label)s_%(class)s",
        parent_link=True,
    )

    deeply_nested_poll = models.ForeignKey(DeeplyNestedPoll, on_delete=models.CASCADE)

    def __str__(self):
        return str(self.deeply_nested_poll)


class ManytoManyPollPlugin(CMSPlugin):
    cmsplugin_ptr = models.OneToOneField(
        CMSPlugin,
        on_delete=models.CASCADE,
        related_name="%(app_label)s_%(class)s",
        parent_link=True,
    )

    polls = models.ManyToManyField(Poll)

    def __str__(self):
        return str(self.polls.first())
