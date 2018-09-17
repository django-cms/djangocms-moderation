from djangocms_versioning.admin import VersionAdmin


def _get_moderation_link(self, obj):
    return 'submit for moderation'


def get_state_actions(func):
    """
    Monkey patch VersionAdmin's get_state_actions to remove publish link,
    as we don't want publishing in moderation
    """
    def inner(self):
        links = func(self)
        links = [link for link in links if link != self._get_publish_link]
        return links + [self._get_moderation_link]
    return inner


VersionAdmin.get_state_actions = get_state_actions(VersionAdmin.get_state_actions)
VersionAdmin._get_moderation_link = _get_moderation_link
