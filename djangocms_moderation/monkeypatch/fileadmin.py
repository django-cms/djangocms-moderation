import filer
from filer.admin.fileadmin import FileAdminChangeFrom

from djangocms_moderation.helpers import (
    get_active_moderation_request,
    is_registered_for_moderation,
)


def init(func):
    def inner(self, *args, **kwargs):
        func(self, *args, **kwargs)

        if is_registered_for_moderation(self.instance) and get_active_moderation_request(self.instance):
            for name, field in self.fields.items():
                field.disabled = True
    return inner

filer.admin.fileadmin.FileAdminChangeFrom.__init__ = init(
    filer.admin.fileadmin.FileAdminChangeFrom.__init__
)
