from __future__ import unicode_literals

from django.conf.urls import url
from django.contrib import admin, messages
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.utils.html import format_html, format_html_join
from django.utils.translation import ugettext, ugettext_lazy as _

from cms.admin.placeholderadmin import PlaceholderAdminMixin
from cms.extensions import PageExtensionAdmin
from cms.models import Page

from adminsortable2.admin import SortableInlineAdminMixin

from . import views
from .constants import ACTION_APPROVED, ACTION_CANCELLED, ACTION_REJECTED
from .forms import WorkflowStepInlineFormSet
from .helpers import (
    get_active_moderation_request,
    get_form_submission_for_step,
    get_page_or_404,
    is_moderation_enabled,
)
from .models import (
    ConfirmationFormSubmission,
    ConfirmationPage,
    PageModeration,
    PageModerationRequest,
    PageModerationRequestAction,
    Role,
    Workflow,
    WorkflowStep,
)


try:
    PageAdmin = admin.site._registry[Page].__class__
except KeyError:
    from cms.admin.pageadmin import PageAdmin


class PageModerationAdmin(PageExtensionAdmin):
    list_display = ['workflow', 'grant_on', 'enabled']
    fields = ['workflow', 'grant_on', 'enabled']


class PageModerationRequestActionInline(admin.TabularInline):
    model = PageModerationRequestAction
    fields = ['show_user', 'message', 'date_taken', 'form_submission']
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

    def form_submission(self, obj):
        instance = get_form_submission_for_step(obj.request, obj.step_approved)

        if not instance:
            return ''

        opts = ConfirmationFormSubmission._meta
        url = reverse('admin:{}_{}_change'.format(opts.app_label, opts.model_name), args=[instance.pk,])
        return format_html('<a href="{}" target="_blank">{}</a>',
            url,
            obj.step_approved.role.name
        )
    form_submission.short_description = _('Form Submission')


class PageModerationRequestAdmin(admin.ModelAdmin):
    inlines = [PageModerationRequestActionInline]
    list_display = ['reference_number', 'page', 'language', 'workflow', 'show_status', 'date_sent']
    list_filter = ['language', 'workflow']
    fields = ['reference_number', 'workflow', 'page', 'language', 'is_active', 'show_status']
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
    list_display = ['name', 'user', 'group', 'confirmation_page']
    fields = ['name', 'user', 'group', 'confirmation_page']


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
    fields = ['name', 'is_default', 'reference_number_backend']


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
            _url(
                r'^([0-9]+)/([a-z\-]+)/moderation/select-workflow/$',
                views.select_new_moderation_request,
                'select_new_moderation',
            ),
            _url(
                r'^([0-9]+)/([a-z\-]+)/moderation/comments/$',
                views.moderation_comments,
                'comments',
            ),
        ]
        return url_patterns + super(ExtendedPageAdmin, self).get_urls()

    def publish_page(self, request, page_id, language):
        page = get_page_or_404(page_id, language)

        if not is_moderation_enabled(page):
            return super(ExtendedPageAdmin, self).publish_page(request, page_id, language)

        active_request = get_active_moderation_request(page, language)

        if active_request and active_request.is_approved:
            # The moderation request has been approved.
            # Let the user publish the page.
            return super(ExtendedPageAdmin, self).publish_page(request, page_id, language)
        elif active_request:
            message = ugettext('This page is currently undergoing moderation '
                               'and can\'t be published until all parties have approved it.')
        else:
            message = ugettext('You need to submit this page for moderation before publishing.')

        messages.warning(request, message)
        path = page.get_absolute_url(language, fallback=True)
        return HttpResponseRedirect(path)


class ConfirmationPageAdmin(PlaceholderAdminMixin, admin.ModelAdmin):
    view_on_site = True

    def get_urls(self):
        def _url(regex, fn, name, **kwargs):
            return url(regex, self.admin_site.admin_view(fn), kwargs=kwargs, name=name)

        url_patterns = [
            _url(r'^moderation-confirmation-page/([0-9]+)/$',
                views.moderation_confirmation_page,
                name='cms_moderation_confirmation_page',
            ),
        ]
        return url_patterns + super(ConfirmationPageAdmin, self).get_urls()


class ConfirmationFormSubmissionAdmin(admin.ModelAdmin):
    list_display = ['moderation_request', 'for_step', 'submitted_at']
    fields = ['moderation_request', 'show_user', 'for_step', 'submitted_at', 'form_data']
    readonly_fields = fields

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
    
    def change_view(self, request, object_id, form_url='', extra_context=None):
        extra_context = extra_context or {}
        extra_context['show_save'] = False
        extra_context['show_save_and_continue'] = False
        return super(ConfirmationFormSubmissionAdmin, self).change_view(
            request, object_id, form_url, extra_context=extra_context,
        )

    def moderation_request(self, obj):
        return obj.request.reference_number
    moderation_request.short_description = _('Request')

    def show_user(self, obj):
        return obj.get_by_user_name()
    show_user.short_description = _('By User')

    def form_data(self, obj):
        data = obj.get_form_data()
        return format_html_join('', '<p>{}: <b>{}</b><br />{}: <b>{}</b></p>',
            ((ugettext('Question'), d['label'], ugettext('Answer'), d['value']) for d in data)
        )
    form_data.short_description = _('Form Data')


admin.site._registry[Page] = ExtendedPageAdmin(Page, admin.site)
admin.site.register(PageModeration, PageModerationAdmin)
admin.site.register(PageModerationRequest, PageModerationRequestAdmin)
admin.site.register(Role, RoleAdmin)
admin.site.register(Workflow, WorkflowAdmin)
admin.site.register(ConfirmationPage, ConfirmationPageAdmin)
admin.site.register(ConfirmationFormSubmission, ConfirmationFormSubmissionAdmin)
