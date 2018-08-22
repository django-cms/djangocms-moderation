from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.utils.translation import ugettext_lazy as _, ungettext

from djangocms_moderation import constants


def resubmit_selected(modeladmin, request, queryset):
    num_resubmitted = 0

    for moderation_request in queryset.all():
        if moderation_request.user_can_resubmit(request.user):
            num_resubmitted += 1
            moderation_request.update_status(
                action=constants.ACTION_RESUBMITTED,
                by_user=request.user,
            )

    messages.success(
        request,
        ungettext(
            '%(count)d request successfully resubmitted for review',
            '%(count)d requests successfully resubmitted for review',
            num_resubmitted
        ) % {
            'count': num_resubmitted
        },
    )


def reject_selected(modeladmin, request, queryset):
    num_rejected = 0

    for moderation_request in queryset.all():
        if moderation_request.user_can_take_moderation_action(request.user):
            num_rejected += 1
            moderation_request.update_status(
                action=constants.ACTION_REJECTED,
                by_user=request.user,
            )

    messages.success(
        request,
        ungettext(
            '%(count)d request successfully rejected',
            '%(count)d requests successfully rejected',
            num_rejected
        ) % {
            'count': num_rejected
        },
    )


def approve_selected(modeladmin, request, queryset):
    num_approved = 0

    for moderation_request in queryset.all():
        if moderation_request.user_can_take_moderation_action(request.user):
            num_approved += 1
            moderation_request.update_status(
                action=constants.ACTION_APPROVED,
                by_user=request.user,
            )

    messages.success(
        request,
        ungettext(
            '%(count)d request successfully approved',
            '%(count)d requests successfully approved',
            num_approved
        ) % {
            'count': num_approved
        },
    )


def delete_selected(modeladmin, request, queryset):
    if not modeladmin.has_delete_permission(request):
        raise PermissionDenied

    if queryset.exclude(collection__author=request.user).exists():
        raise PermissionDenied

    num_deleted_requests = queryset.count()
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


publish_selected.short_description = _("Publish selected requests")


def publish_content_object(content_object):
    # TODO: e.g.moderation_request.content_object.publish(request.user)
    return True
