from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.utils.translation import ugettext_lazy as _, ungettext

from djangocms_moderation import constants
from djangocms_moderation.emails import (
    notify_collection_author,
    notify_collection_moderators,
)


def resubmit_selected(modeladmin, request, queryset):
    """
    Validate and re-submit all the selected moderation requests for
    moderation and notify reviewers via email.
    """
    resubmitted_requests = []

    for mr in queryset.all():
        if mr.user_can_resubmit(request.user):
            resubmitted_requests.append(mr)
            mr.update_status(
                action=constants.ACTION_RESUBMITTED,
                by_user=request.user,
            )

    if resubmitted_requests:
        # Lets notify reviewers. TODO task queue?
        notify_collection_moderators(
            collection=request._collection,
            moderation_requests=resubmitted_requests,
            # We can take any action here, as all the requests are in the same
            # stage of moderation - at the beginning
            action_obj=resubmitted_requests[0].get_last_action()
        )

    messages.success(
        request,
        ungettext(
            '%(count)d request successfully resubmitted for review',
            '%(count)d requests successfully resubmitted for review',
            len(resubmitted_requests)
        ) % {
            'count': len(resubmitted_requests)
        },
    )


resubmit_selected.short_description = _("Resubmit changes for review")


def reject_selected(modeladmin, request, queryset):
    """
    Validate and reject all the selected moderation requests and notify
    the author about these requests
    """
    rejected_requests = []

    for moderation_request in queryset.all():
        if moderation_request.user_can_take_moderation_action(request.user):
            rejected_requests.append(moderation_request)
            moderation_request.update_status(
                action=constants.ACTION_REJECTED,
                by_user=request.user,
            )

    # Now we need to notify collection reviewers and moderator. TODO task queue?
    if rejected_requests:
        notify_collection_author(
            collection=request._collection,
            moderation_requests=rejected_requests,
            action=constants.ACTION_REJECTED,
            by_user=request.user,
        )

    messages.success(
        request,
        ungettext(
            '%(count)d request successfully submitted for rework',
            '%(count)d requests successfully submitted for rework',
            len(rejected_requests)
        ) % {
            'count': len(rejected_requests)
        },
    )


reject_selected.short_description = _('Submit for rework')


def approve_selected(modeladmin, request, queryset):
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
    approved_requests = []
    # Variable we are using to group the requests by action.step_approved
    request_action_mapping = dict()

    for mr in queryset.all():
        if mr.user_can_take_moderation_action(request.user):
            approved_requests.append(mr)
            mr.update_status(
                action=constants.ACTION_APPROVED,
                by_user=request.user,
            )
            action = mr.get_last_action()
            if action.to_user_id or action.to_role_id:
                step_approved_str = str(action.step_approved)
                if step_approved_str not in request_action_mapping:
                    request_action_mapping[step_approved_str] = [mr]
                    request_action_mapping['action_' + step_approved_str] = action
                else:
                    request_action_mapping[step_approved_str].append(mr)

    if approved_requests:  # TODO task queue?
        # Lets notify the collection author about the approval
        notify_collection_author(
            collection=request._collection,
            moderation_requests=approved_requests,
            action=constants.ACTION_APPROVED,
            by_user=request.user,
        )

        # Notify reviewers
        for key, moderation_requests in request_action_mapping.items():
            if not key.startswith('action_'):
                notify_collection_moderators(
                    collection=request._collection,
                    moderation_requests=moderation_requests,
                    action_obj=request_action_mapping['action_' + key]
                )

    messages.success(
        request,
        ungettext(
            '%(count)d request successfully approved',
            '%(count)d requests successfully approved',
            len(approved_requests)
        ) % {
            'count': len(approved_requests)
        },
    )

    post_bulk_actions(request._collection)


def delete_selected(modeladmin, request, queryset):
    if not modeladmin.has_delete_permission(request):
        raise PermissionDenied

    if queryset.exclude(collection__author=request.user).exists():
        raise PermissionDenied

    num_deleted_requests = queryset.count()

    if num_deleted_requests:  # TODO task queue?
        notify_collection_author(
            collection=request._collection,
            moderation_requests=[mr for mr in queryset],
            action=constants.ACTION_CANCELLED,
            by_user=request.user,
        )

    queryset.delete()
    messages.success(
        request,
        ungettext(
            '%(count)d request successfully deleted',
            '%(count)d requests successfully deleted',
            num_deleted_requests
        ) % {
            'count': num_deleted_requests
        },
    )

    post_bulk_actions(request._collection)


delete_selected.short_description = _('Cancel selected')


def publish_selected(modeladmin, request, queryset):
    if request.user != request._collection.author:
        raise PermissionDenied

    num_published_requests = 0
    for moderation_request in queryset.all():
        if moderation_request.is_approved():
            num_published_requests += 1
            publish_content_object(moderation_request.content_object)

    # notify the UI of the action results
    messages.success(
        request,
        ungettext(
            '%(count)d request successfully published',
            '%(count)d requests successfully published',
            num_published_requests
        ) % {
            'count': num_published_requests
        },
    )

    post_bulk_actions(request._collection)


publish_selected.short_description = _("Publish selected requests")


def post_bulk_actions(collection):
    if collection.should_be_archived():
        collection.status = constants.ARCHIVED
        collection.save(update_fields=['status'])


def publish_content_object(content_object):
    # TODO: e.g.moderation_request.content_object.publish(request.user)
    return True
