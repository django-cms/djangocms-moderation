from collections import defaultdict

from django.contrib import messages
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.http import HttpResponseRedirect
from django.utils.translation import ugettext_lazy as _, ungettext

from cms.utils.urlutils import add_url_parameters

from django_fsm import TransitionNotAllowed
from djangocms_versioning.models import Version

from djangocms_moderation import constants
from djangocms_moderation.emails import (
    notify_collection_author,
    notify_collection_moderators,
)

from .utils import get_admin_url


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
resubmit_selected.short_description = _("Resubmit changes for review")  # noqa: E305


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
    # request._collection is passed down from change_list from admin.py
    # https://github.com/divio/djangocms-moderation/pull/46#discussion_r211569629
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
reject_selected.short_description = _('Submit for rework')  # noqa: E305


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
                # We group the moderation requests by step_approved.pk.
                # Sometimes it can be None, in which case they can be grouped
                # together and we use "0" as a key
                step_approved_key = str(action.step_approved.pk if action.step_approved else 0)
                if step_approved_key not in request_action_mapping:
                    request_action_mapping[step_approved_key] = [mr]
                    request_action_mapping['action_' + step_approved_key] = action
                else:
                    request_action_mapping[step_approved_key].append(mr)

    if approved_requests:  # TODO task queue?
        # Lets notify the collection author about the approval
        # request._collection is passed down from change_list from admin.py
        # https://github.com/divio/djangocms-moderation/pull/46#discussion_r211569629
        notify_collection_author(
            collection=request._collection,
            moderation_requests=approved_requests,
            action=constants.ACTION_APPROVED,
            by_user=request.user,
        )

        # Notify reviewers
        for key, moderation_requests in sorted(request_action_mapping.items(), key=lambda x: x[0]):
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
delete_selected.short_description = _('Remove selected')  # noqa: E305


def publish_selected(modeladmin, request, queryset):
    if request.user != request._collection.author:
        raise PermissionDenied

    num_published_requests = 0
    for mr in queryset.all():
        if mr.version_can_be_published():
            if publish_version(mr.version, request.user):
                num_published_requests += 1
                mr.update_status(
                    action=constants.ACTION_FINISHED,
                    by_user=request.user,
                )
            else:
                # TODO provide some feedback back to the user?
                pass

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
publish_selected.short_description = _("Publish selected requests")  # noqa: E305


def haystack_queryset_to_version_queryset(queryset):
    """Returns the version objects corresponding to the objects in the Haystack queryset"""
    id_map = defaultdict(list)
    for obj in queryset:
        id_map[obj.model].append(obj.pk)
    q = Q()
    for obj_model, ids in id_map.items():
        ctype = ContentType.objects.get_for_model(obj_model)
        q |= Q(content_type=ctype, object_id__in=ids)
    return Version.objects.filter(q)


def add_items_to_collection(modeladmin, request, queryset):
    """
    Action to add queryset to moderation collection. Note that queryset is a
    Haystack SearchQuerySet
    """
    version_ids = haystack_queryset_to_version_queryset(queryset).values_list('pk', flat=True)
    version_ids = [str(x) for x in version_ids]
    if version_ids:
        admin_url = add_url_parameters(
            get_admin_url(
                name='cms_moderation_items_to_collection',
                language=request.GET.get('language'),
                args=()
            ), version_ids=','.join(version_ids),
            return_to_url=request.META.get('HTTP_REFERER'))
        return HttpResponseRedirect(admin_url)
    else:
        modeladmin.message_user(request, _("No suitable items found to add to moderation collection"))
        return HttpResponseRedirect(request.META.get('HTTP_REFERER'))
add_items_to_collection.short_description = _("Add to moderation collection")  # noqa: E305


def post_bulk_actions(collection):
    if collection.should_be_archived():
        collection.status = constants.ARCHIVED
        collection.save(update_fields=['status'])


def publish_version(version, user):
    try:
        version.publish(user)
    except TransitionNotAllowed:
        return False
    return True
