from __future__ import unicode_literals

from django.conf.urls import url
from django.contrib import admin
from django.core.urlresolvers import reverse
from django.http import Http404
from django.utils.html import format_html, format_html_join
from django.utils.translation import ugettext, ugettext_lazy as _

from cms.admin.placeholderadmin import PlaceholderAdminMixin

from adminsortable2.admin import SortableInlineAdminMixin

from djangocms_moderation.constants import IN_REVIEW, ARCHIVED
from .admin_actions import (
    delete_selected,
    publish_selected,
    approve_selected,
    reject_selected,
    resubmit_selected,
)
from .forms import WorkflowStepInlineFormSet
from .helpers import get_form_submission_for_step
from .models import (
    ConfirmationFormSubmission,
    ConfirmationPage,
    ModerationCollection,
    ModerationRequest,
    ModerationRequestAction,
    Role,
    Workflow,
    WorkflowStep,
)


from . import views  # isort:skip


class ModerationRequestActionInline(admin.TabularInline):
    model = ModerationRequestAction
    fields = ['show_user', 'message', 'date_taken', 'form_submission']
    readonly_fields = fields
    verbose_name = _('Action')
    verbose_name_plural = _('Actions')

    def has_add_permission(self, request):
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
        url = reverse(
            'admin:{}_{}_change'.format(opts.app_label, opts.model_name),
            args=[instance.pk],
        )
        return format_html(
            '<a href="{}" target="_blank">{}</a>',
            url,
            obj.step_approved.role.name
        )
    form_submission.short_description = _('Form Submission')


class ModerationRequestAdmin(admin.ModelAdmin):
    actions = [  # filtered out in `self.get_actions`
        delete_selected,
        publish_selected,
        approve_selected,
        reject_selected,
        resubmit_selected,
    ]
    inlines = [ModerationRequestActionInline]
    list_display = ['id', 'content_type', 'get_title', 'collection', 'get_preview_link', 'get_status']
    fields = ['id', 'collection', 'workflow', 'is_active', 'get_status']
    readonly_fields = fields
    change_list_template = 'djangocms_moderation/moderation_request_change_list.html'

    def has_module_permission(self, request):
        """
        Don't display Requests in the admin index as they should be accessed
        and filtered through the Collection list view
        """
        return False

    def get_title(self, obj):
        return obj.content_object
    get_title.short_description = _('Title')

    def get_preview_link(self, obj):
        # TODO this will return Version object preview link once implemented
        return "Link placeholder"
    get_preview_link.short_description = _('Preview')

    def has_add_permission(self, request):
        return False

    def get_actions(self, request):
        """
        By default, all actions are enabled. But we need to only keep the actions
        which have a moderation requests ready for.
        E.g. if there are no moderation requests ready to be published,
        we don't need to keep the `publish_selected` action
        """
        try:
            collection = request._collection
        except AttributeError:
            # If we are not in the collection aware list, then don't
            # offer any bulk actions
            return None

        actions = super().get_actions(request)
        actions_to_keep = []

        # Only collection author can delete moderation requests
        if collection.author == request.user:
            actions_to_keep.append('delete_selected')

        if collection.status in [IN_REVIEW, ARCHIVED]:
            # Keep track how many actions we've added in the below loop (_actions_kept).
            # If we added all of them (_max_to_keep), we can exit the for loop
            _actions_kept = 0
            if collection.status == IN_REVIEW:
                _max_to_keep = 4  # publish_selected, approve_selected, reject_selected, resubmit_selected
            else:
                # If the collection is archived, then no other action than
                # `publish_selected` is possible.
                _max_to_keep = 1  # publish_selected

            for mr in collection.moderation_requests.all():
                if _actions_kept == _max_to_keep:
                    break  # We have found all the actions, so no need to loop anymore
                if 'publish_selected' not in actions_to_keep:
                    if mr.is_approved() and request.user == collection.author:
                        actions_to_keep.append('publish_selected')
                        _actions_kept += 1
                if collection.status == IN_REVIEW and 'approve_selected' not in actions_to_keep:
                    if mr.user_can_take_moderation_action(request.user):
                        actions_to_keep.append('approve_selected')
                        actions_to_keep.append('reject_selected')
                        _actions_kept += 2
                if collection.status == IN_REVIEW and 'resubmit_selected' not in actions_to_keep:
                    if mr.user_can_resubmit(request.user):
                        actions_to_keep.append('resubmit_selected')
                        _actions_kept += 1

        return {
            key: value for key, value in actions.items() if key in actions_to_keep
        }

    def changelist_view(self, request, extra_context=None):
        # If we filter by a specific collection, we want to add this collection
        # to the context
        collection_id = request.GET.get('collection__id__exact')
        if collection_id:
            try:
                collection = ModerationCollection.objects.get(pk=int(collection_id))
                request._collection = collection
            except (ValueError, ModerationCollection.DoesNotExist):
                pass
            else:
                extra_context = dict(collection=collection)
                if collection.allow_submit_for_review(user=request.user):
                    submit_for_review_url = reverse(
                        'admin:cms_moderation_submit_collection_for_moderation',
                        args=(collection_id,)
                    )
                    extra_context['submit_for_review_url'] = submit_for_review_url
        else:
            # If no collection id, then don't show all requests
            # as each collection's actions, buttons and privileges may differ
            raise Http404

        return super().changelist_view(request, extra_context)

    def get_status(self, obj):
        # We can have moderation requests without any action (e.g. the
        # ones not submitted for moderation yet)
        last_action = obj.get_last_action()

        if last_action:
            if obj.is_approved():
                status = ugettext('Ready for publishing')
            # TODO: consider published status for version e.g.:
            # elif obj.content_object.is_published():
            #     status = ugettext('Published')
            elif obj.is_rejected():
                status = ugettext('Pending author rework')
            elif obj.is_active and obj.has_pending_step():
                next_step = obj.get_next_required()
                role = next_step.role.name
                status = ugettext('Pending %(role)s approval') % {'role': role}
            else:
                user_name = last_action.get_by_user_name()
                message_data = {
                    'action': last_action.get_action_display(),
                    'name': user_name,
                }
                status = ugettext('%(action)s by %(name)s') % message_data
        else:
            status = ugettext('Ready for submission')
        return status
    get_status.short_description = _('Status')


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
    fields = [
        'name',
        'is_default',
        'identifier',
        'requires_compliance_number',
        'compliance_number_backend',
    ]


class ModerationCollectionAdmin(admin.ModelAdmin):
    actions = None  # remove `delete_selected` for now, it will be handled later
    list_display = [
        'id',
        'get_name_with_requests_link',
        'job_id',
        'get_moderator',
        'workflow',
        'status',
        'date_created',
    ]
    editonly_fields = ('status',)  # fields editable only on EDIT
    addonly_fields = ('workflow',)  # fields editable only on CREATE

    def get_readonly_fields(self, request, obj=None):
        """
        Override to provide editonly_fields and addonly_fields functionality
        """
        if obj:  # Editing an existing object
            return self.readonly_fields + self.addonly_fields
        else:  # Adding a new object
            return self.readonly_fields + self.editonly_fields

    def get_name_with_requests_link(self, obj):
        """
        Name of the collection should link to the list of associated
        moderation requests
        """
        return format_html(
            '<a href="{}?collection__id__exact={}">{}</a>',
            reverse('admin:djangocms_moderation_moderationrequest_changelist'),
            obj.pk,
            obj.name,
        )
    get_name_with_requests_link.short_description = _('Name')

    def get_moderator(self, obj):
        return obj.author
    get_moderator.short_description = _('Moderator')

    def get_urls(self):
        def _url(regex, fn, name, **kwargs):
            return url(regex, self.admin_site.admin_view(fn), kwargs=kwargs, name=name)

        url_patterns = [
            _url(
                '^(?P<collection_id>\d+)/submit-for-review/$',
                views.submit_collection_for_moderation,
                name="cms_moderation_submit_collection_for_moderation",
            ),
            _url(
                r'^item/add-item/$',
                views.add_item_to_collection,
                name='cms_moderation_item_to_collection',
            )
        ]
        return url_patterns + super().get_urls()


class ConfirmationPageAdmin(PlaceholderAdminMixin, admin.ModelAdmin):
    view_on_site = True

    def get_urls(self):
        def _url(regex, fn, name, **kwargs):
            return url(regex, self.admin_site.admin_view(fn), kwargs=kwargs, name=name)

        url_patterns = [
            _url(
                r'^moderation-confirmation-page/([0-9]+)/$',
                views.moderation_confirmation_page,
                name='cms_moderation_confirmation_page',
            ),
        ]
        return url_patterns + super().get_urls()


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
        return super().change_view(
            request, object_id, form_url, extra_context=extra_context,
        )

    def moderation_request(self, obj):
        return obj.request_id
    moderation_request.short_description = _('Request')

    def show_user(self, obj):
        return obj.get_by_user_name()
    show_user.short_description = _('By User')

    def form_data(self, obj):
        data = obj.get_form_data()
        return format_html_join(
            '',
            '<p>{}: <b>{}</b><br />{}: <b>{}</b></p>',
            ((ugettext('Question'), d['label'], ugettext('Answer'), d['value']) for d in data)
        )
    form_data.short_description = _('Form Data')


admin.site.register(ModerationRequest, ModerationRequestAdmin)
admin.site.register(ModerationCollection, ModerationCollectionAdmin)
admin.site.register(Role, RoleAdmin)
admin.site.register(Workflow, WorkflowAdmin)

admin.site.register(ConfirmationPage, ConfirmationPageAdmin)
admin.site.register(ConfirmationFormSubmission, ConfirmationFormSubmissionAdmin)
