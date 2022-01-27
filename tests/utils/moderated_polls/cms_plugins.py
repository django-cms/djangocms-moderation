from cms.plugin_base import CMSPluginBase
from cms.plugin_pool import plugin_pool

from .models import PollPlugin as Poll, NestedPollPlugin as NestedPoll


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
    render_template = "polls/poll.html"
