import string

from cms.models import Placeholder

import factory
from djangocms_versioning.models import Version
from djangocms_versioning.test_utils.factories import AbstractVersionFactory
from factory.fuzzy import FuzzyChoice, FuzzyInteger, FuzzyText

from .moderated_polls.models import Poll, PollContent, PollPlugin
from .versioned_none_moderated_app.models import NoneModeratedPoll, NoneModeratedPollContent, NoneModeratedPollPlugin


def get_plugin_position(plugin):
    """Helper function to correctly calculate the plugin position.
    Use this in plugin factory classes
    """
    offset = plugin.placeholder.get_last_plugin_position(
        plugin.language) or 0
    return offset + 1


def get_plugin_language(plugin):
    """Helper function to get the language from a plugin's relationships.
    Use this in plugin factory classes
    """
    if plugin.placeholder.source:
        return plugin.placeholder.source.language
    # NOTE: If plugin.placeholder.source is None then language will
    # also be None unless set manually


class PlaceholderFactory(factory.django.DjangoModelFactory):
    default_width = FuzzyInteger(0, 25)
    slot = FuzzyText(length=2, chars=string.digits)
    # NOTE: When using this factory you will probably want to set
    # the source field manually

    class Meta:
        model = Placeholder


class PollFactory(factory.django.DjangoModelFactory):
    name = FuzzyText(length=6)

    class Meta:
        model = Poll


class PollContentFactory(factory.django.DjangoModelFactory):
    poll = factory.SubFactory(PollFactory)
    language = FuzzyChoice(['en', 'fr', 'it'])
    text = FuzzyText(length=24)

    class Meta:
        model = PollContent


class PollPluginFactory(factory.django.DjangoModelFactory):
    language = factory.LazyAttribute(get_plugin_language)
    placeholder = factory.SubFactory(PlaceholderFactory)
    parent = None
    position = factory.LazyAttribute(get_plugin_position)
    plugin_type = 'PollPlugin'
    poll = factory.SubFactory(PollFactory)

    class Meta:
        model = PollPlugin


class PollVersionFactory(AbstractVersionFactory):
    content = factory.SubFactory(PollContentFactory)

    class Meta:
        model = Version

# None Moderated Poll App factories


class NoneModeratedPollFactory(factory.django.DjangoModelFactory):
    name = FuzzyText(length=6)

    class Meta:
        model = NoneModeratedPoll


class NoneModeratedPollContentFactory(factory.django.DjangoModelFactory):
    poll = factory.SubFactory(NoneModeratedPollFactory)
    language = FuzzyChoice(['en', 'fr', 'it'])
    text = FuzzyText(length=24)

    class Meta:
        model = NoneModeratedPollContent


class NoneModeratedPollVersionFactory(AbstractVersionFactory):
    content = factory.SubFactory(NoneModeratedPollContentFactory)

    class Meta:
        model = Version


class NoneModeratedPollPluginFactory(factory.django.DjangoModelFactory):
    language = factory.LazyAttribute(get_plugin_language)
    placeholder = factory.SubFactory(PlaceholderFactory)
    parent = None
    position = factory.LazyAttribute(get_plugin_position)
    plugin_type = 'NoneModeratedPollPlugin'
    poll = factory.SubFactory(NoneModeratedPollFactory)

    class Meta:
        model = NoneModeratedPollPlugin
