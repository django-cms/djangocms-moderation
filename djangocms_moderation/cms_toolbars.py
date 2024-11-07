from django.contrib.auth import get_permission_codename
from django.utils.translation import gettext_lazy as _

from cms.cms_toolbars import ADMIN_MENU_IDENTIFIER
from cms.utils.urlutils import add_url_parameters

from djangocms_versioning.cms_toolbars import VersioningToolbar, replace_toolbar
from djangocms_versioning.models import Version

from . import helpers
from .models import ModerationCollection, ModerationRequest
from .utils import get_admin_url


class ModerationToolbar(VersioningToolbar):
    class Media:
        # Media keeps all the settings from the parent class, so we only need
        # to add moderation media here
        # https://docs.djangoproject.com/en/2.1/topics/forms/media/#extend
        js = ("djangocms_moderation/js/dist/bundle.moderation.min.js",)
        css = {"all": ("djangocms_moderation/css/moderation.css",)}

    def _add_publish_button(self):
        """
        Disable djangocms_versioning publish button if we can moderate content object
        """
        if not helpers.is_registered_for_moderation(self.toolbar.obj):
            return super()._add_publish_button()

    def _add_edit_button(self, disabled=False):
        """
        Add edit button if we can moderate content object
        Or add a disabled edit button when object is 'Review locked'
        """
        # can we moderate content object?
        # return early to avoid further DB calls below
        if not helpers.is_registered_for_moderation(self.toolbar.obj):
            return super()._add_edit_button(disabled=disabled)

        # yes we can! but is it locked?
        if helpers.is_obj_review_locked(self.toolbar.obj, self.request.user):
            disabled = True

        # disabled if locked, else default to false
        return super()._add_edit_button(disabled=disabled)

    def _add_moderation_buttons(self):
        """
        Add submit for moderation button if we can moderate content object
        and toolbar is in edit mode

        Display the collection name when object is in moderation
        """
        if not helpers.is_registered_for_moderation(self.toolbar.obj):
            return

        if self._is_versioned() and (self.toolbar.edit_mode_active or self.toolbar.preview_mode_active):
            moderation_request = helpers.get_active_moderation_request(self.toolbar.obj)
            if moderation_request:
                title, url = helpers.get_moderation_button_title_and_url(
                    moderation_request
                )
                self.toolbar.add_sideframe_button(
                    name=title, url=url, side=self.toolbar.RIGHT
                )
            # Check if the object is not version locked to someone else
            elif helpers.is_obj_version_unlocked(self.toolbar.obj, self.request.user):
                opts = ModerationRequest._meta
                codename = get_permission_codename("add", opts)
                if not self.request.user.has_perm(
                    f"{opts.app_label}.{codename}"
                ):
                    return
                version = Version.objects.get_for_content(self.toolbar.obj)
                url = add_url_parameters(
                    get_admin_url(
                        name="cms_moderation_items_to_collection",
                        language=self.current_lang,
                        args=(),
                    ),
                    version_ids=version.pk,
                )
                self.toolbar.add_modal_button(
                    name=_("Submit for moderation"), url=url, side=self.toolbar.RIGHT
                )

    def _add_moderation_menu(self):
        """
        Helper method to add moderation menu in the toolbar
        """
        opts = ModerationCollection._meta
        codename = get_permission_codename("change", opts)
        if not self.request.user.has_perm(
            f"{opts.app_label}.{codename}"
        ):
            return
        admin_menu = self.toolbar.get_or_create_menu(ADMIN_MENU_IDENTIFIER)
        url = get_admin_url(
            "djangocms_moderation_moderationcollection_changelist",
            language=self.current_lang,
            args=(),
        )
        # if the current user is a moderator or reviewer, then create a link
        # which will filter to show only collections for that user's attention
        if helpers.get_all_moderators().filter(pk=self.request.user.id).exists():
            url += "?moderator=%s" % self.request.user.id
        elif helpers.get_all_reviewers().filter(pk=self.request.user.id).exists():
            url += "?reviewer=%s" % self.request.user.id
        admin_menu.add_sideframe_item(_("Moderation collections"), url=url, position=3)

    def post_template_populate(self):
        super().post_template_populate()
        self._add_moderation_buttons()
        self._add_moderation_menu()


replace_toolbar(VersioningToolbar, ModerationToolbar)
