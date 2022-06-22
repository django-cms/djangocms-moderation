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
    ManytoManyPollPlugin,
    NestedPoll,
    NestedPollPlugin,
)


class NestedPollFactory(DjangoModelFactory):
    poll = factory.SubFactory(PollFactory)

    class Meta:
        model = NestedPoll


class ManytoManyPollPluginFactory(DjangoModelFactory):
    language = factory.LazyAttribute(get_plugin_language)
    placeholder = factory.SubFactory(PlaceholderFactory)
    parent = None
    position = factory.LazyAttribute(get_plugin_position)
    plugin_type = "ManytoManyPollPlugin"

    class Meta:
        model = ManytoManyPollPlugin

    @factory.post_generation
    def polls(self, create, extracted, **kwargs):
        if not create:
            # Simple build, do nothing.
            return

        if extracted:
            # A list of groups were passed in, use them
            for poll in extracted:
                self.polls.add(poll)


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
