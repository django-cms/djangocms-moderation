import factory

from factory.django import DjangoModelFactory

from .models import NestedPoll, NestedPollPlugin
from ..factories import (
    get_plugin_position,
    get_plugin_language,
    PlaceholderFactory,
    PollFactory,
)


class NestedPollFactory(DjangoModelFactory):
    poll = factory.SubFactory(PollFactory)

    class Meta:
        model = NestedPoll


class NestedPollPluginFactory(DjangoModelFactory):
    language = factory.LazyAttribute(get_plugin_language)
    placeholder = factory.SubFactory(PlaceholderFactory)
    parent = None
    position = factory.LazyAttribute(get_plugin_position)
    plugin_type = "NestedPollPlugin"
    nested_poll = factory.SubFactory(NestedPollFactory)

    class Meta:
        model = NestedPollPlugin
