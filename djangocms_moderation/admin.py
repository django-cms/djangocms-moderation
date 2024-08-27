from django import forms
from django.apps import apps
from django.contrib import admin, messages
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.http import Http404, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.template.loader import render_to_string
from django.urls import re_path, reverse
from django.utils.html import format_html, format_html_join
from django.utils.translation import gettext, gettext_lazy as _, ngettext

from cms.admin.placeholderadmin import PlaceholderAdminMixin
from cms.toolbar.utils import get_object_preview_url
from cms.utils.helpers import is_editable_model

from adminsortable2.admin import SortableAdminBase, SortableInlineAdminMixin
from treebeard.admin import TreeAdmin

from . import constants, signals
from .admin_actions import (
    approve_selected,
    delete_selected,
    post_bulk_actions,
    publish_selected,
    publish_version,
    reject_selected,
    resubmit_selected,
)
from .emails import notify_collection_author, notify_collection_moderators
from .filters import ModeratorFilter, ReviewerFilter
from .forms import (
    CollectionCommentForm,
    ModerationRequestActionInlineForm,
    RequestCommentForm,
    WorkflowStepInlineFormSet,
)
from .helpers import get_form_submission_for_step
from .models import (
    CollectionComment,
    ConfirmationFormSubmission,
    ConfirmationPage,
    ModerationCollection,
    ModerationRequest,
    ModerationRequestAction,
    ModerationRequestTreeNode,
    RequestComment,
    Role,
    Workflow,
    WorkflowStep,
)


from . import conf  # isort:skip
from . import utils  # isort:skip
from . import views  # isort:skip

User = get_user_model()


class ModerationRequestActionInline(admin.TabularInline):
    model = ModerationRequestAction
    form = ModerationRequestActionInlineForm
    fields = ["show_user", "message", "date_taken", "form_submission"]
    verbose_name = _("Action")
    verbose_name_plural = _("Actions")

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    @admin.display(
        description=_("Status")
    )
    def show_user(self, obj):
        _name = obj.get_by_user_name()
        return gettext("By {user}").format(user=_name)

    @admin.display(
        description=_("Form Submission")
    )
    def form_submission(self, obj):
        instance = get_form_submission_for_step(
            obj.moderation_request, obj.step_approved
        )

        if not instance:
            return ""

        opts = ConfirmationFormSubmission._meta
        url = reverse(
            f"admin:{opts.app_label}_{opts.model_name}_change",
            args=[instance.pk],
        )
        return format_html(
            '<a href="{}" target="_blank">{}</a>', url, obj.step_approved.role.name
        )

    def get_readonly_fields(self, request, obj=None):
        if obj.user_can_moderate(request.user) or obj.user_is_author(request.user):
            # Omit 'message' from readonly_fields when current user is a reviewer
            # or an author. This disallows a non-participant from
            # adding or editing comments on action objects
            return ["show_user", "date_taken", "form_submission"]
        return self.fields


@admin.register(ModerationRequestTreeNode)
class ModerationRequestTreeAdmin(TreeAdmin):
    """
    This admin is purely for the change list of Moderation Requests using the treebeard nodes to
    organise the requests into a nested structure which also allows moderation requests to be displayed
    more than once, i.e. they are present in more than one parent.
    """
    class Media:
        js = (
            "admin/js/jquery.init.js",
            "djangocms_moderation/js/actions.js",
            "djangocms_moderation/js/burger.js",
        )
        css = {
            "all": ("djangocms_moderation/css/actions.css", "djangocms_moderation/css/burger.css")
        }

    actions = [  # filtered out in `self.get_actions`
        delete_selected,
        publish_selected,
        approve_selected,
        reject_selected,
        resubmit_selected,
    ]
    change_list_template = 'djangocms_moderation/moderation_request_change_list.html'
    list_display_links = []

    def has_add_permission(self, request):
        """
        Disable the add button by returning false
        """
        return False

    def has_module_permission(self, request):
        """
        Don't display Requests in the admin index as they should be accessed
        and filtered through the Collection list view
        """
        return False

    def lookup_allowed(self, lookup, value):
        if lookup in ('moderation_request__collection__id',):
            return True
        return super().lookup_allowed(lookup)

    def get_urls(self):
        info = self.model._meta.app_label, self.model._meta.model_name

        return [
            re_path(
                r'^delete_selected/',
                self.admin_site.admin_view(self.delete_selected_view),
                name='{}_{}_delete'.format(*info),
            ),
        ] + super().get_urls()

    def get_list_display(self, request):
        additional_fields = self._get_configured_fields(request)
        list_display = [
            'get_id',
            'get_content_type',
            'get_title',
            'get_version_author',
            'get_preview_link',
            'get_status',
            'get_reviewer',
            *additional_fields,
            'list_display_actions',
        ]
        return list_display

    @admin.display(
        description=_("actions")
    )
    def list_display_actions(self, obj):
        """Display links to state change endpoints
        """
        return format_html_join(
            "", "{}", ((action(obj),) for action in self.get_list_display_actions())
        )

    def get_list_display_actions(self):
        actions = []
        if conf.REQUEST_COMMENTS_ENABLED:
            actions.append(self.get_comments_link)

        # Get any configured additional actions
        moderation_config = apps.get_app_config("djangocms_moderation")
        additional_actions = moderation_config.cms_extension.moderation_request_changelist_actions
        if additional_actions:
            actions += additional_actions

        return actions

    def _get_configured_fields(self, request):
        fields = []
        moderation_config = apps.get_app_config("djangocms_moderation")
        additional_fields = moderation_config.cms_extension.moderation_request_changelist_fields

        for field in additional_fields:
            fields.append(field.__name__)
            setattr(self, field.__name__, field)

        return fields

    @admin.display(
        description=_('ID')
    )
    def get_id(self, obj):
        return format_html(
            '<a href="{url}">{id}</a>',
            url=reverse(
                'admin:djangocms_moderation_moderationrequest_change',
                args=(obj.moderation_request_id,),
            ),
            id=obj.moderation_request_id,
        )

    @admin.display(
        description=_('Content type')
    )
    def get_content_type(self, obj):
        return ContentType.objects.get_for_model(
            obj.moderation_request.version.versionable.grouper_model
        )

    @admin.display(
        description=_('Title')
    )
    def get_title(self, obj):
        return obj.moderation_request.version.content

    @admin.display(
        description=_('Author')
    )
    def get_version_author(self, obj):
        return obj.moderation_request.version.created_by

    @admin.display(
        description=_("Preview")
    )
    def get_preview_link(self, obj):
        content = obj.moderation_request.version.content
        if is_editable_model(content.__class__):
            object_preview_url = get_object_preview_url(content)
        else:
            object_preview_url = reverse(
                "admin:{app}_{model}_change".format(
                    app=content._meta.app_label, model=content._meta.model_name
                ),
                args=[content.pk],
            )

        return format_html(
            '<a href="{}" class="js-moderation-close-sideframe" target="_top">'
            '<span class="cms-icon cms-icon-eye"></span>'
            "</a>",
            object_preview_url,
        )

    @admin.display(
        description=_('Reviewer')
    )
    def get_reviewer(self, obj):
        last_action = obj.moderation_request.get_last_action()
        if not last_action:
            return
        if obj.moderation_request.is_active and obj.moderation_request.has_pending_step():
            next_step = obj.moderation_request.get_next_required()
            return next_step.role.name
        return last_action._get_user_name(last_action.by_user)

    def get_status(self, obj):
        # We can have moderation requests without any action (e.g. the
        # ones not submitted for moderation yet)
        last_action = obj.moderation_request.get_last_action()

        if last_action:
            if obj.moderation_request.version_can_be_published():
                status = gettext('Ready for publishing')
            elif obj.moderation_request.is_rejected():
                status = gettext('Pending author rework')
            elif obj.moderation_request.is_active and obj.moderation_request.has_pending_step():
                next_step = obj.moderation_request.get_next_required()
                role = next_step.role.name
                status = gettext('Pending %(role)s approval') % {'role': role}
            elif not obj.moderation_request.version.can_be_published():
                status = obj.moderation_request.version.get_state_display()
            else:
                user_name = last_action.get_by_user_name()
                message_data = {
                    'action': last_action.get_action_display(),
                    'name': user_name,
                }
                status = gettext('%(action)s by %(name)s') % message_data
        else:
            status = gettext('Ready for submission')
        return status

    def get_comments_link(self, obj):
        comments_endpoint = format_html(
            "{}?moderation_request__id__exact={}",
            reverse("admin:djangocms_moderation_requestcomment_changelist"),
            obj.moderation_request.id,
        )
        return render_to_string(
            "djangocms_moderation/comment_icon.html", {"url": comments_endpoint}
        )

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
            return {}

        actions = super().get_actions(request)
        actions_to_keep = []

        if collection.status in [constants.IN_REVIEW, constants.ARCHIVED]:
            # Keep track how many actions we've added in the below loop (_actions_kept).
            # If we added all of them (_max_to_keep), we can exit the for loop
            if collection.status == constants.IN_REVIEW:
                _max_to_keep = (
                    4
                )  # publish_selected, approve_selected, reject_selected, resubmit_selected
            else:
                # If the collection is archived, then no other action than
                # `publish_selected` is possible.
                _max_to_keep = 1  # publish_selected

            for mr in collection.moderation_requests.all().select_related("version"):
                if len(actions_to_keep) == _max_to_keep:
                    break  # We have found all the actions, so no need to loop anymore
                if "publish_selected" not in actions_to_keep:
                    if (
                        request.user == collection.author
                        and mr.version_can_be_published()
                    ):
                        actions_to_keep.append("publish_selected")
                if (
                    collection.status == constants.IN_REVIEW
                    and "approve_selected" not in actions_to_keep
                ):
                    if mr.user_can_take_moderation_action(request.user):
                        actions_to_keep.append("approve_selected")
                        actions_to_keep.append("reject_selected")
                if (
                    collection.status == constants.IN_REVIEW
                    and "resubmit_selected" not in actions_to_keep
                ):
                    if mr.user_can_resubmit(request.user):
                        actions_to_keep.append("resubmit_selected")

        # Only collection author can delete moderation requests
        if collection.author == request.user:
            actions_to_keep.append("remove_selected")

        return {key: value for key, value in actions.items() if key in actions_to_keep}

    def changelist_view(self, request, extra_context=None):
        # If we filter by a specific collection, we want to add this collection
        # to the context
        collection_id = request.GET.get('moderation_request__collection__id')
        if not collection_id:
            # If no collection id, then don't show all requests
            # as each collection's actions, buttons and privileges may differ
            raise Http404
        try:
            collection = ModerationCollection.objects.get(pk=int(collection_id))
            request._collection = collection
        except (ValueError, ModerationCollection.DoesNotExist):
            pass
        else:
            extra_context = dict(collection=collection)
            if collection.is_cancellable(request.user):
                cancel_collection_url = reverse(
                    'admin:cms_moderation_cancel_collection',
                    args=(collection_id,)
                )
                extra_context['cancel_collection_url'] = cancel_collection_url

            if collection.allow_submit_for_review(user=request.user):
                submit_for_review_url = reverse(
                    'admin:cms_moderation_submit_collection_for_moderation',
                    args=(collection_id,)
                )
                extra_context['submit_for_review_url'] = submit_for_review_url

        return super().changelist_view(request, extra_context)

    @transaction.atomic
    def delete_selected_view(self, request):
        if not self.has_delete_permission(request):
            raise PermissionDenied

        # TODO: What if this is None
        collection_id = request.GET.get('collection_id')
        # TODO: 404?
        collection = ModerationCollection.objects.get(pk=collection_id)
        if collection.author != request.user:
            raise PermissionDenied

        moderation_requests_affected = []

        # For each moderation request id, if one has a tree structure attached go through each one and remove that!
        # Get all of the nodes selected to delete
        queryset = ModerationRequestTreeNode.objects.filter(pk__in=request.GET.get('ids', '').split(','))

        def _traverse_moderation_nodes(node_item):
            moderation_requests_affected.append(node_item.moderation_request.pk)

            # Recurse over children if they exist
            children = node_item.get_children()
            for child in children:
                _traverse_moderation_nodes(child)

        for node in queryset.all():
            _traverse_moderation_nodes(node)

        queryset = ModerationRequest.objects.filter(pk__in=moderation_requests_affected)
        redirect_url = reverse('admin:djangocms_moderation_moderationrequesttreenode_changelist')
        redirect_url = "{}?moderation_request__collection__id={}".format(
            redirect_url,
            collection_id
        )

        if request.method != 'POST':
            context = dict(
                ids=request.GET.getlist('ids'),
                back_url=redirect_url,
                queryset=queryset,
            )
            return render(request, 'admin/djangocms_moderation/moderationrequest/delete_confirmation.html', context)
        else:
            try:
                collection = ModerationCollection.objects.get(id=int(collection_id))
            except (ValueError, ModerationCollection.DoesNotExist):
                raise Http404

            num_deleted_requests = queryset.count()
            if num_deleted_requests:
                notify_collection_author(
                    collection=collection,
                    moderation_requests=[mr for mr in queryset],
                    action=constants.ACTION_CANCELLED,
                    by_user=request.user,
                )

            queryset.delete()
            messages.success(
                request,
                ngettext(
                    '%(count)d request successfully deleted',
                    '%(count)d requests successfully deleted',
                    num_deleted_requests
                ) % {
                    'count': num_deleted_requests
                },
            )
            post_bulk_actions(collection)

        return HttpResponseRedirect(redirect_url)


@admin.register(ModerationRequest)
class ModerationRequestAdmin(admin.ModelAdmin):
    class Media:
        js = ('admin/js/jquery.init.js', 'djangocms_moderation/js/actions.js',)

    inlines = [ModerationRequestActionInline]

    def _redirect_to_changeview_url(self, collection_id):
        """
        An internal private helper that generates a return url to this models changeview.
        """
        redirect_url = reverse('admin:djangocms_moderation_moderationrequesttreenode_changelist')
        return "{}?moderation_request__collection__id={}".format(
            redirect_url,
            collection_id
        )

    def get_formsets_with_inlines(self, request, obj=None):
        for inline in self.get_inline_instances(request, obj):
            inline.form.current_user = request.user
            yield inline.get_formset(request, obj), inline

    def has_module_permission(self, request):
        """
        Don't display Requests in the admin index as they should be accessed
        and filtered through the Collection list view
        """
        return False

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        """
        Hide the delete button from the detail page and prevent a MR from being deleted in the admin.
        """
        return False

    def get_urls(self):
        info = self.model._meta.app_label, self.model._meta.model_name

        return [
            re_path(
                r"^approve/",
                self.admin_site.admin_view(self.approved_view),
                name="{}_{}_approve".format(*info),
            ),
            re_path(
                r"^rework/",
                self.admin_site.admin_view(self.rework_view),
                name="{}_{}_rework".format(*info),
            ),
            re_path(
                r"^publish/",
                self.admin_site.admin_view(self.published_view),
                name="{}_{}_publish".format(*info),
            ),
            re_path(
                r"^resubmit/",
                self.admin_site.admin_view(self.resubmit_view),
                name="{}_{}_resubmit".format(*info),
            ),
        ] + super().get_urls()

    def _get_selected_tree_nodes(self, request):
        treenodes = ModerationRequestTreeNode.objects.filter(
            pk__in=request.GET.get('ids', '').split(',')
        ).select_related('moderation_request')
        return treenodes

    def _custom_view_context(self, request):
        treenodes = self._get_selected_tree_nodes(request)
        collection_id = request.GET.get('collection_id')
        redirect_url = self._redirect_to_changeview_url(collection_id)
        return dict(
            ids=request.GET.getlist("ids"),
            back_url=redirect_url,
            queryset=[n.moderation_request for n in treenodes]
        )

    def resubmit_view(self, request):
        collection_id = request.GET.get('collection_id')
        treenodes = self._get_selected_tree_nodes(request)
        redirect_url = self._redirect_to_changeview_url(collection_id)

        try:
            collection = ModerationCollection.objects.get(id=int(collection_id))
        except (ValueError, ModerationCollection.DoesNotExist):
            raise Http404

        if collection.author != request.user:
            raise PermissionDenied

        if request.method != 'POST':
            context = self._custom_view_context(request)
            return render(
                request,
                'admin/djangocms_moderation/moderationrequest/resubmit_confirmation.html',
                context
            )
        else:
            resubmitted_requests = []

            for node in treenodes.all():
                mr = node.moderation_request
                if mr.user_can_resubmit(request.user):
                    resubmitted_requests.append(mr)
                    mr.update_status(
                        action=constants.ACTION_RESUBMITTED, by_user=request.user
                    )

            if resubmitted_requests:
                # Lets notify reviewers. TODO task queue?
                notify_collection_moderators(
                    collection=collection,
                    moderation_requests=resubmitted_requests,
                    # We can take any action here, as all the requests are in the same
                    # stage of moderation - at the beginning
                    action_obj=resubmitted_requests[0].get_last_action(),
                )
                signals.submitted_for_review.send(
                    sender=collection.__class__,
                    collection=collection,
                    moderation_requests=resubmitted_requests,
                    user=request.user,
                    rework=True,
                )

            messages.success(
                request,
                ngettext(
                    "%(count)d request successfully resubmitted for review",
                    "%(count)d requests successfully resubmitted for review",
                    len(resubmitted_requests),
                )
                % {"count": len(resubmitted_requests)},
            )
        return HttpResponseRedirect(redirect_url)

    @transaction.atomic
    def published_view(self, request):
        collection_id = request.GET.get('collection_id')
        redirect_url = self._redirect_to_changeview_url(collection_id)

        try:
            collection = ModerationCollection.objects.get(id=int(collection_id))
        except (ValueError, ModerationCollection.DoesNotExist):
            raise Http404

        if request.user != collection.author:
            raise PermissionDenied

        if request.method != 'POST':
            context = self._custom_view_context(request)
            return render(
                request,
                "admin/djangocms_moderation/moderationrequest/publish_confirmation.html",
                context,
            )
        else:
            treenodes = self._get_selected_tree_nodes(request)

            published_moderation_requests = []
            for node in treenodes.all():
                mr = node.moderation_request
                if mr.version_can_be_published():
                    if publish_version(mr.version, request.user):
                        published_moderation_requests.append(mr)
                        mr.update_status(
                            action=constants.ACTION_FINISHED, by_user=request.user
                        )
                    else:
                        # TODO provide some feedback back to the user?
                        pass

            messages.success(
                request,
                ngettext(
                    "%(count)d request successfully published",
                    "%(count)d requests successfully published",
                    len(published_moderation_requests),
                )
                % {"count": len(published_moderation_requests)},
            )

            post_bulk_actions(collection)
            signals.published.send(
                sender=self.model,
                collection=collection,
                moderator=collection.author,
                moderation_requests=published_moderation_requests,
                workflow=collection.workflow
            )

        return HttpResponseRedirect(redirect_url)

    def rework_view(self, request):
        collection_id = request.GET.get('collection_id')
        treenodes = self._get_selected_tree_nodes(request)
        redirect_url = self._redirect_to_changeview_url(collection_id)

        if request.method != 'POST':
            context = self._custom_view_context(request)
            return render(
                request,
                "admin/djangocms_moderation/moderationrequest/rework_confirmation.html",
                context,
            )
        else:
            try:
                collection = ModerationCollection.objects.get(id=int(collection_id))
            except (ValueError, ModerationCollection.DoesNotExist):
                raise Http404

            rejected_requests = []

            for node in treenodes.all():
                moderation_request = node.moderation_request
                if moderation_request.user_can_take_moderation_action(request.user):
                    rejected_requests.append(moderation_request)
                    moderation_request.update_status(
                        action=constants.ACTION_REJECTED, by_user=request.user
                    )

            # Now we need to notify collection reviewers and moderator. TODO task queue?
            # https://github.com/divio/djangocms-moderation/pull/46#discussion_r211569629
            if rejected_requests:
                notify_collection_author(
                    collection=collection,
                    moderation_requests=rejected_requests,
                    action=constants.ACTION_REJECTED,
                    by_user=request.user,
                )

            messages.success(
                request,
                ngettext(
                    "%(count)d request successfully submitted for rework",
                    "%(count)d requests successfully submitted for rework",
                    len(rejected_requests),
                )
                % {"count": len(rejected_requests)},
            )
        return HttpResponseRedirect(redirect_url)

    def approved_view(self, request):
        collection_id = request.GET.get('collection_id')
        treenodes = self._get_selected_tree_nodes(request)
        redirect_url = self._redirect_to_changeview_url(collection_id)

        if request.method != 'POST':
            context = self._custom_view_context(request)
            return render(
                request,
                "admin/djangocms_moderation/moderationrequest/approve_confirmation.html",
                context,
            )
        else:
            """
            Validate and approve all the selected moderation requests and notify
            the author and reviewers.

            When bulk approving, we need to check for the next line of reviewers and
            notify them about the pending moderation requests assigned to them.

            Because this is a bulk action, we need to group the approved_requests
            by the action.step_approved, so we notify the correct reviewers.

            For example, if some requests are in the first stage of approval,
            and some in the second, then the reviewers we need to notify are
            different per request, depending on which stage the request is in
            """
            try:
                collection = ModerationCollection.objects.get(id=int(collection_id))
            except (ValueError, ModerationCollection.DoesNotExist):
                raise Http404

            approved_requests = []
            # Variable we are using to group the requests by action.step_approved
            request_action_mapping = dict()

            for node in treenodes.all():
                mr = node.moderation_request
                if mr.user_can_take_moderation_action(request.user):
                    approved_requests.append(mr)
                    mr.update_status(
                        action=constants.ACTION_APPROVED, by_user=request.user
                    )
                    action = mr.get_last_action()
                    if action.to_user_id or action.to_role_id:
                        # We group the moderation requests by step_approved.pk.
                        # Sometimes it can be None, in which case they can be grouped
                        # together and we use "0" as a key
                        step_approved_key = str(
                            action.step_approved.pk if action.step_approved else 0
                        )
                        if step_approved_key not in request_action_mapping:
                            request_action_mapping[step_approved_key] = [mr]
                            request_action_mapping[
                                "action_" + step_approved_key
                            ] = action
                        else:
                            request_action_mapping[step_approved_key].append(mr)

            if approved_requests:  # TODO task queue?
                # Lets notify the collection author about the approval
                # request._collection is passed down from change_list from admin.py
                # https://github.com/divio/djangocms-moderation/pull/46#discussion_r211569629
                notify_collection_author(
                    collection=collection,
                    moderation_requests=approved_requests,
                    action=constants.ACTION_APPROVED,
                    by_user=request.user,
                )

                # Notify reviewers
                for key, moderation_requests in sorted(
                    request_action_mapping.items(), key=lambda x: x[0]
                ):
                    if not key.startswith("action_"):
                        notify_collection_moderators(
                            collection=collection,
                            moderation_requests=moderation_requests,
                            action_obj=request_action_mapping["action_" + key],
                        )

            messages.success(
                request,
                ngettext(
                    "%(count)d request successfully approved",
                    "%(count)d requests successfully approved",
                    len(approved_requests),
                )
                % {"count": len(approved_requests)},
            )

            post_bulk_actions(collection)

        return HttpResponseRedirect(redirect_url)

    def changelist_view(self, request, extra_context=None):
        """
        Redirects silently to the tree node changelist.
        """
        tree_node_admin = admin.site._registry[ModerationRequestTreeNode]
        return tree_node_admin.changelist_view(request, extra_context)


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ["name", "user", "group", "confirmation_page"]
    fields = ["name", "user", "group", "confirmation_page"]


@admin.register(CollectionComment)
class CollectionCommentAdmin(admin.ModelAdmin):
    list_display = ["date_created", "message", "author"]
    fields = ["collection", "message", "author"]

    class Media:
        css = {"all": ("djangocms_moderation/css/comments_changelist.css",)}

    def get_changeform_initial_data(self, request):
        data = {"author": request.user}
        # Extract the id from the URL. The id is stored in _changelist_filters
        # by Django so that the request knows where to return to after form submission.
        collection_id = utils.extract_filter_param_from_changelist_url(
            request, "_changelist_filters", "collection__id__exact"
        )
        if collection_id:
            data["collection"] = collection_id
        else:
            raise Http404

        return data

    def get_form(self, request, obj=None, **kwargs):
        return CollectionCommentForm

    def has_module_permission(self, request):
        """
        Hide the model from admin index as it depends on foreighKey
        """
        return False

    def changelist_view(self, request, extra_context=None):
        # If we filter by a specific collection, we want to add this collection
        # to the context
        collection_id = request.GET.get("collection__id__exact")
        if collection_id:
            try:
                collection = ModerationCollection.objects.get(pk=int(collection_id))
                request._collection = collection
            except (ValueError, ModerationCollection.DoesNotExist):
                raise Http404
            else:
                extra_context = dict(
                    collection=collection, title=_("Collection comments")
                )
        else:
            raise Http404
        return super().changelist_view(request, extra_context)

    def changeform_view(self, request, object_id=None, form_url="", extra_context=None):
        # get the collection for the breadcrumb trail
        collection_id = utils.extract_filter_param_from_changelist_url(
            request, "_changelist_filters", "collection__id__exact"
        )

        extra_context = extra_context or dict(
            show_save_and_add_another=False, show_save_and_continue=False
        )
        if object_id:
            try:
                collection_comment = get_object_or_404(
                    CollectionComment, pk=int(object_id)
                )
            except ValueError:
                raise Http404
            if request.user != collection_comment.author:
                extra_context["readonly"] = True

        if collection_id:
            extra_context["collection_id"] = collection_id
        else:
            raise Http404

        return super().changeform_view(request, object_id, form_url, extra_context)

    def has_delete_permission(self, request, obj=None):
        return request.user == getattr(obj, "author", None)

    def get_readonly_fields(self, request, obj=None):
        if obj and request.user != obj.author:
            return self.list_display


@admin.register(RequestComment)
class RequestCommentAdmin(admin.ModelAdmin):
    list_display = ["date_created", "message", "get_author"]
    fields = ["moderation_request", "message", "author"]

    class Media:
        css = {"all": ("djangocms_moderation/css/comments_changelist.css",)}

    @admin.display(
        description=_("User")
    )
    def get_author(self, obj):
        return obj.author_name

    def get_changeform_initial_data(self, request):
        data = {"author": request.user}
        moderation_request_id = utils.extract_filter_param_from_changelist_url(
            request, "_changelist_filters", "moderation_request__id__exact"
        )
        if moderation_request_id:
            data["moderation_request"] = moderation_request_id
        return data

    def get_form(self, request, obj=None, **kwargs):
        return RequestCommentForm

    def has_module_permission(self, request):
        """
        Hide the model from admin index as it depends on foreighKey
        """
        return False

    def changelist_view(self, request, extra_context=None):
        # If we filter by a specific collection, we want to add this collection
        # to the context
        moderation_request_id = request.GET.get("moderation_request__id__exact")
        if moderation_request_id:
            try:
                moderation_request = ModerationRequest.objects.get(
                    pk=int(moderation_request_id)
                )
                collection = moderation_request.collection
                request._collection = collection
            except (ValueError, ModerationRequest.DoesNotExist):
                raise Http404
            else:
                extra_context = dict(collection=collection, title=_("Request comments"))
        else:
            # If no collection id, then don't show all requests
            # as each collection's actions, buttons and privileges may differ
            raise Http404
        return super().changelist_view(request, extra_context)

    def changeform_view(self, request, object_id=None, form_url="", extra_context=None):
        extra_context = extra_context or dict(
            show_save_and_add_another=False, show_save_and_continue=False
        )
        if object_id:
            try:
                request_comment = get_object_or_404(RequestComment, pk=int(object_id))
            except ValueError:
                raise Http404
            if request.user != request_comment.author:
                extra_context["readonly"] = True
        # for breadcrumb trail
        moderation_request_id = utils.extract_filter_param_from_changelist_url(
            request, "_changelist_filters", "moderation_request__id__exact"
        )
        if moderation_request_id:
            extra_context["moderation_request_id"] = moderation_request_id
            mr = ModerationRequest.objects.get(pk=int(moderation_request_id))
            extra_context["collection_id"] = mr.collection.id
        return super().changeform_view(request, object_id, form_url, extra_context)

    def has_delete_permission(self, request, obj=None):
        return request.user == getattr(obj, "author", None)

    def get_readonly_fields(self, request, obj=None):
        if obj and request.user != obj.author:
            return self.list_display


class WorkflowStepInline(SortableInlineAdminMixin, admin.TabularInline):
    formset = WorkflowStepInlineFormSet
    model = WorkflowStep

    def get_extra(self, request, obj=None, **kwargs):
        if obj and obj.pk:
            return 0
        return 1


@admin.register(Workflow)
class WorkflowAdmin(SortableAdminBase, admin.ModelAdmin):
    inlines = [WorkflowStepInline]
    list_display = ["name", "is_default"]
    fields = [
        "name",
        "is_default",
        "identifier",
        "requires_compliance_number",
        "compliance_number_backend",
    ]


@admin.register(ModerationCollection)
class ModerationCollectionAdmin(admin.ModelAdmin):
    class Media:
        js = ("admin/js/jquery.init.js", "djangocms_moderation/js/actions.js",)
        css = {"all": ("djangocms_moderation/css/actions.css",)}

    actions = None  # remove `delete_selected` for now, it will be handled later
    list_filter = [ModeratorFilter, "status", "date_created", ReviewerFilter]
    list_display_links = None
    list_per_page = 100

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        qs = qs.prefetch_reviewers()
        return qs

    def get_list_display(self, request):
        list_display = [
            "job_id",
            "name",
            "author",
            "workflow",
            "status",
            "commaseparated_reviewers",
            "date_created",
            "list_display_actions",
        ]
        return list_display

    def job_id(self, obj):
        return obj.pk

    @admin.display(
        description=_('reviewers')
    )
    def commaseparated_reviewers(self, obj):
        reviewers = self.model.objects.reviewers(obj)
        return ", ".join(map(get_user_model().get_full_name, reviewers))

    @admin.display(
        description=_("actions")
    )
    def list_display_actions(self, obj):
        """Display links to state change endpoints
        """
        return format_html_join(
            "", "{}", ((action(obj),) for action in self.get_list_display_actions())
        )

    def get_list_display_actions(self):
        actions = [self.get_edit_link, self.get_requests_link]
        if conf.COLLECTION_COMMENTS_ENABLED:
            actions.append(self.get_comments_link)
        return actions

    def change_view(self, request, object_id, form_url="", extra_context=None):
        extra_context = {"title": _("Modify collection")}
        return super().change_view(
            request, object_id, form_url, extra_context=extra_context
        )

    def get_edit_link(self, obj):
        """Helper function to get the html link to the edit action
        """
        url = reverse(
            "admin:djangocms_moderation_moderationcollection_change", args=[obj.pk]
        )
        return render_to_string("djangocms_moderation/edit_icon.html", {"url": url})

    def get_requests_link(self, obj):
        """
        Name of the collection should link to the list of associated
        moderation requests
        """
        url = format_html(
            "{}?moderation_request__collection__id={}",
            reverse("admin:djangocms_moderation_moderationrequest_changelist"),
            obj.pk,
        )
        return render_to_string("djangocms_moderation/request_icon.html", {"url": url})

    def get_comments_link(self, obj):
        edit_url = format_html(
            "{}?collection__id__exact={}",
            reverse("admin:djangocms_moderation_collectioncomment_changelist"),
            obj.pk,
        )
        return render_to_string(
            "djangocms_moderation/comment_icon.html", {"url": edit_url}
        )

    def get_urls(self):
        def _url(regex, fn, name, **kwargs):
            return re_path(regex, self.admin_site.admin_view(fn), kwargs=kwargs, name=name)

        url_patterns = [
            _url(
                r"^(?P<collection_id>\d+)/submit-for-review/$",
                views.submit_collection_for_moderation,
                name="cms_moderation_submit_collection_for_moderation",
            ),
            _url(
                r"^(?P<collection_id>\d+)/cancel-collection/$",
                views.cancel_collection,
                name="cms_moderation_cancel_collection",
            ),
            _url(
                r"^item/add-items/$",
                views.add_items_to_collection,
                name="cms_moderation_items_to_collection",
            ),
        ]
        return url_patterns + super().get_urls()

    def get_changeform_initial_data(self, request):
        return {"author": request.user}

    def get_readonly_fields(self, request, obj=None):
        readonly_fields = ["status"]
        if obj:
            if not request.user.has_perm("djangocms_moderation.can_change_author"):
                readonly_fields.append("author")
            # Author of the collection can change the workflow if the collection
            # is still in the `collecting` state
            if obj.status != constants.COLLECTING or obj.author != request.user:
                readonly_fields.append("workflow")
        return readonly_fields

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if obj and "author" in self.readonly_fields:
            form.base_fields["author"].widget = forms.HiddenInput()
        return form

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ConfirmationPage)
class ConfirmationPageAdmin(PlaceholderAdminMixin, admin.ModelAdmin):
    view_on_site = True

    def get_urls(self):
        def _url(regex, fn, name, **kwargs):
            return re_path(regex, self.admin_site.admin_view(fn), kwargs=kwargs, name=name)

        url_patterns = [
            _url(
                r"^moderation-confirmation-page/([0-9]+)/$",
                views.moderation_confirmation_page,
                name="cms_moderation_confirmation_page",
            )
        ]
        return url_patterns + super().get_urls()


@admin.register(ConfirmationFormSubmission)
class ConfirmationFormSubmissionAdmin(admin.ModelAdmin):
    list_display = ["moderation_request", "for_step", "submitted_at"]
    fields = [
        "moderation_request",
        "show_user",
        "for_step",
        "submitted_at",
        "form_data",
    ]
    readonly_fields = fields

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def change_view(self, request, object_id, form_url="", extra_context=None):
        extra_context = extra_context or {}
        extra_context["show_save"] = False
        extra_context["show_save_and_continue"] = False
        return super().change_view(
            request, object_id, form_url, extra_context=extra_context
        )

    @admin.display(
        description=_("Request")
    )
    def moderation_request(self, obj):
        return obj.moderation_request_id

    @admin.display(
        description=_("By User")
    )
    def show_user(self, obj):
        return obj.get_by_user_name()

    @admin.display(
        description=_("Form Data")
    )
    def form_data(self, obj):
        data = obj.get_form_data()
        return format_html_join(
            "",
            "<p>{}: <b>{}</b><br />{}: <b>{}</b></p>",
            (
                (gettext("Question"), d["label"], gettext("Answer"), d["value"])
                for d in data
            ),
        )
