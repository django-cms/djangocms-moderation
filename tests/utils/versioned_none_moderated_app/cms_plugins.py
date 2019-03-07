from cms.plugin_base import CMSPluginBase
from cms.plugin_pool import plugin_pool

from .models import NoneModeratedPollPlugin as NoneModeratedPoll


@plugin_pool.register_plugin
class NoneModeratedPollPlugin(CMSPluginBase):
    model = NoneModeratedPoll
    name = "nonemoderatedpoll"
    render_plugin = False
