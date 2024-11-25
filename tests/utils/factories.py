import string

from django.contrib.auth.models import User

from cms.models import Placeholder

import factory
from djangocms_versioning.models import Version
from djangocms_versioning.test_utils.factories import (
    AbstractVersionFactory,
    PageVersionFactory,
)
from factory.django import DjangoModelFactory
from factory.fuzzy import FuzzyChoice, FuzzyInteger, FuzzyText

from djangocms_moderation.models import (
    ModerationCollection,
    ModerationRequest,
    ModerationRequestTreeNode,
    Workflow,
)

from .moderated_polls.models import Poll, PollContent, PollPlugin
from .versioned_none_moderated_app.models import (
    NoneModeratedPoll,
    NoneModeratedPollContent,
    NoneModeratedPollPlugin,
)


def get_plugin_position(plugin):
    """Helper function to correctly calculate the plugin position.
    Use this in plugin factory classes
    """
    offset = plugin.placeholder.get_last_plugin_position(plugin.language) or 0
    return offset + 1


def get_plugin_language(plugin):
    """Helper function to get the language from a plugin's relationships.
    Use this in plugin factory classes
    """
    if plugin.placeholder.source:
        return plugin.placeholder.source.language
    # NOTE: If plugin.placeholder.source is None then language will
    # also be None unless set manually


class PlaceholderFactory(DjangoModelFactory):
    default_width = FuzzyInteger(0, 25)
    slot = FuzzyText(length=2, chars=string.digits)
    # NOTE: When using this factory you will probably want to set
    # the source field manually

    class Meta:
        model = Placeholder


class PollFactory(DjangoModelFactory):
    name = FuzzyText(length=6)

    class Meta:
        model = Poll


class PollContentFactory(DjangoModelFactory):
    poll = factory.SubFactory(PollFactory)
    language = FuzzyChoice(["en", "fr", "it"])
    text = FuzzyText(length=24)

    class Meta:
        model = PollContent


class PollPluginFactory(DjangoModelFactory):
    language = factory.LazyAttribute(get_plugin_language)
    placeholder = factory.SubFactory(PlaceholderFactory)
    parent = None
    position = factory.LazyAttribute(get_plugin_position)
    plugin_type = "PollPlugin"
    poll = factory.SubFactory(PollFactory)

    class Meta:
        model = PollPlugin


class PollVersionFactory(AbstractVersionFactory):
    content = factory.SubFactory(PollContentFactory)

    class Meta:
        model = Version


# None Moderated Poll App factories


class NoneModeratedPollFactory(DjangoModelFactory):
    name = FuzzyText(length=6)

    class Meta:
        model = NoneModeratedPoll


class NoneModeratedPollContentFactory(DjangoModelFactory):
    poll = factory.SubFactory(NoneModeratedPollFactory)
    language = FuzzyChoice(["en", "fr", "it"])
    text = FuzzyText(length=24)

    class Meta:
        model = NoneModeratedPollContent


class NoneModeratedPollVersionFactory(AbstractVersionFactory):
    content = factory.SubFactory(NoneModeratedPollContentFactory)

    class Meta:
        model = Version


class NoneModeratedPollPluginFactory(DjangoModelFactory):
    language = factory.LazyAttribute(get_plugin_language)
    placeholder = factory.SubFactory(PlaceholderFactory)
    parent = None
    position = factory.LazyAttribute(get_plugin_position)
    plugin_type = "NoneModeratedPollPlugin"
    poll = factory.SubFactory(NoneModeratedPollFactory)

    class Meta:
        model = NoneModeratedPollPlugin


class UserFactory(DjangoModelFactory):
    username = FuzzyText(length=12)
    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")
    email = factory.LazyAttribute(
        lambda u: f"{u.first_name.lower()}.{u.last_name.lower()}@example.com"
    )

    class Meta:
        model = User

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        manager = cls._get_manager(model_class)
        return manager.create_user(*args, **kwargs)


class WorkflowFactory(DjangoModelFactory):
    name = FuzzyText(length=12)

    class Meta:
        model = Workflow


class ModerationCollectionFactory(DjangoModelFactory):
    name = FuzzyText(length=12)
    author = factory.SubFactory(UserFactory)
    workflow = factory.SubFactory(WorkflowFactory)

    class Meta:
        model = ModerationCollection


class ModerationRequestFactory(DjangoModelFactory):
    collection = factory.SubFactory(ModerationCollectionFactory)
    version = factory.SubFactory(PageVersionFactory)
    language = 'en'
    author = factory.LazyAttribute(lambda o: o.collection.author)

    class Meta:
        model = ModerationRequest


class RootModerationRequestTreeNodeFactory(DjangoModelFactory):
    moderation_request = factory.SubFactory(ModerationRequestFactory)

    class Meta:
        model = ModerationRequestTreeNode

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        """Make sure this is the root of a tree"""
        return model_class.add_root(*args, **kwargs)


class ChildModerationRequestTreeNodeFactory(DjangoModelFactory):
    moderation_request = factory.SubFactory(ModerationRequestFactory)
    parent = factory.SubFactory(RootModerationRequestTreeNodeFactory)

    class Meta:
        model = ModerationRequestTreeNode
        inline_args = ("parent",)

    @classmethod
    def _create(cls, model_class, parent, *args, **kwargs):
        """Make sure this is the child of a parent node"""
        return parent.add_child(*args, **kwargs)
