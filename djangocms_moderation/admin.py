from __future__ import unicode_literals

from django.contrib import admin
from django.contrib import messages
from django.conf.urls import url
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.utils.translation import ugettext, ugettext_lazy as _

from cms.admin.pageadmin import PageAdmin
from cms.extensions import PageExtensionAdmin
from cms.models import Page

from adminsortable2.admin import SortableInlineAdminMixin

from . import views
from .constants import ACTION_APPROVED, ACTION_CANCELLED, ACTION_REJECTED
from .forms import WorkflowStepInlineFormSet
from .helpers import get_page_moderation_workflow
from .models import (
    PageModeration,
    PageModerationRequest,
    PageModerationRequestAction,
    Role,
    Workflow,
    WorkflowStep,
)


class PageModerationAdmin(PageExtensionAdmin):
    list_display = ['workflow', 'grant_on']
    fields = ['workflow', 'grant_on']


class PageModerationRequestActionInline(admin.TabularInline):
    model = PageModerationRequestAction
    fields = ['show_user', 'message', 'date_taken']
    readonly_fields = fields
    verbose_name = _('Action')
    verbose_name_plural = _('Actions')

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def show_user(self, obj):
        _name = obj.get_by_user_name()
        return ugettext('By {user}').format(user=_name)
    show_user.short_description = _('Status')


class PageModerationRequestAdmin(admin.ModelAdmin):
    inlines = [PageModerationRequestActionInline]
    list_display = ['page', 'language', 'workflow', 'show_status', 'date_sent']
    list_filter = ['language', 'workflow']
    fields = ['workflow', 'page', 'language', 'is_active', 'show_status']
    readonly_fields = fields

    def has_add_permission(self, request):
        return False

    def show_status(self, obj):
        if obj.is_approved:
            status = ugettext('Ready for publishing')
        elif obj.is_active and obj.has_pending_step:
            next_step = obj.get_next_required()
            role = next_step.role.name
            status = ugettext('Pending %(role)s approval') % {'role': role}
        else:
            last_action = obj.get_last_action()
            user_name = last_action.get_by_user_name()
            message_data = {
                'action': last_action.get_action_display(),
                'name': user_name,
            }
            status = ugettext('%(action)s by %(name)s') % message_data
        return status
    show_status.short_description = _('Status')


class RoleAdmin(admin.ModelAdmin):
    list_display = ['name', 'user', 'group']
    fields = ['name', 'user', 'group']


class WorkflowStepInline(SortableInlineAdminMixin, admin.TabularInline):
    formset = WorkflowStepInlineFormSet
    model = WorkflowStep

    def get_extra(self, request, obj=None, **kwargs):
        if obj and obj.pk:
            return 0
        return 1


class WorkflowAdmin(admin.ModelAdmin):
    inlines = [WorkflowStepInline]
    list_display = ['name', 'is_default']
    fields = ['name', 'is_default']


class ExtendedPageAdmin(PageAdmin):

    def get_urls(self):
        def _url(regex, fn, name, **kwargs):
            name = 'cms_moderation_{}'.format(name)
            return url(regex, self.admin_site.admin_view(fn), kwargs=kwargs, name=name)

        url_patterns = [
            _url(
                r'^([0-9]+)/([a-z\-]+)/moderation/new/$',
                views.new_moderation_request,
                'new_request',
            ),
            _url(
                r'^([0-9]+)/([a-z\-]+)/moderation/cancel/$',
                views.cancel_moderation_request,
                'cancel_request',
                action=ACTION_CANCELLED
            ),
            _url(
                r'^([0-9]+)/([a-z\-]+)/moderation/reject/$',
                views.reject_moderation_request,
                'reject_request',
                action=ACTION_REJECTED
            ),
            _url(
                r'^([0-9]+)/([a-z\-]+)/moderation/approve/$',
                views.approve_moderation_request,
                'approve_request',
                action=ACTION_APPROVED,
            ),
        ]
        return url_patterns + super(ExtendedPageAdmin, self).get_urls()

    def publish_page(self, request, page_id, language):
        page = get_object_or_404(
            Page,
            pk=page_id,
            publisher_is_draft=True,
            title_set__language=language,
        )

        workflow = get_page_moderation_workflow(page)

        if not workflow:
            return super(ExtendedPageAdmin, self).publish_page(request, page_id, language)

        active_request = workflow.get_active_request(page, language)

        if active_request and active_request.is_approved:
            # The moderation request has been approved.
            # Let the user publish the page.
            return super(ExtendedPageAdmin, self).publish_page(request, page_id, language)
        elif active_request:
            message = ugettext('This page is currently undergoing moderation '
                               'and can\'t be published until all parties have approved it.')
        else:
            message = ugettext('You need to submit this page to moderation before publishing.')

        messages.warning(request, message)
        path = page.get_absolute_url(language, fallback=True)
        return HttpResponseRedirect(path)


try:
    admin.site.unregister(Page)
finally:
    admin.site.register(Page, ExtendedPageAdmin)

admin.site.register(PageModeration, PageModerationAdmin)
admin.site.register(PageModerationRequest, PageModerationRequestAdmin)
admin.site.register(Role, RoleAdmin)
admin.site.register(Workflow, WorkflowAdmin)
