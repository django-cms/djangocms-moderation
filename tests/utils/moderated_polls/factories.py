import factory
from factory.django import DjangoModelFactory

from ..factories import (
    PlaceholderFactory,
    PollFactory,
    get_plugin_language,
    get_plugin_position,
)
from .models import (
    DeeplyNestedPoll,
    DeeplyNestedPollPlugin,
    NestedPoll,
    NestedPollPlugin,
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


class DeeplyNestedPollFactory(DjangoModelFactory):
    nested_poll = factory.SubFactory(NestedPollFactory)

    class Meta:
        model = DeeplyNestedPoll


class DeeplyNestedPollPluginFactory(DjangoModelFactory):
    language = factory.LazyAttribute(get_plugin_language)
    placeholder = factory.SubFactory(PlaceholderFactory)
    parent = None
    position = factory.LazyAttribute(get_plugin_position)
    plugin_type = "DeeplyNestedPollPlugin"
    deeply_nested_poll = factory.SubFactory(DeeplyNestedPollFactory)

    class Meta:
        model = DeeplyNestedPollPlugin
