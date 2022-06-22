from cms.plugin_base import CMSPluginBase
from cms.plugin_pool import plugin_pool

from .models import (
    DeeplyNestedPollPlugin as DeeplyNestedPoll,
    ManytoManyPollPlugin as ManytoManyPoll,
    NestedPollPlugin as NestedPoll,
    PollPlugin as Poll,
)


@plugin_pool.register_plugin
class PollPlugin(CMSPluginBase):
    model = Poll
    name = "Poll"
    allow_children = True
    render_template = "polls/poll.html"


@plugin_pool.register_plugin
class NestedPollPlugin(CMSPluginBase):
    model = NestedPoll
    name = "NestedPoll"
    allow_children = True
    render_template = "polls/nested_poll.html"


@plugin_pool.register_plugin
class DeeplyNestedPollPlugin(CMSPluginBase):
    model = DeeplyNestedPoll
    name = "DeeplyNestedPoll"
    allow_children = True
    render_template = "polls/deeply_nested_poll.html"


@plugin_pool.register_plugin
class ManytoManyPollPlugin(CMSPluginBase):
    model = ManytoManyPoll
    name = "ManytoManyPoll"
    allow_children = True
    render_template = "polls/many_polls.html"
