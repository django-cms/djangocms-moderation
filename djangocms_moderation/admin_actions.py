from collections import defaultdict
from functools import partial

from django.contrib.admin.helpers import ACTION_CHECKBOX_NAME
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.http import HttpResponseRedirect
from django.shortcuts import reverse
from django.utils.translation import gettext_lazy as _

from cms.utils.urlutils import add_url_parameters

from django_fsm import TransitionNotAllowed
from djangocms_versioning.models import Version

from djangocms_moderation import constants

from .utils import get_admin_url


def resubmit_selected(modeladmin, request, queryset):
    """
    Validate and re-submit all the selected moderation requests for
    moderation and notify reviewers via email.
    """
    selected = request.POST.getlist(ACTION_CHECKBOX_NAME)
    url = "{}?ids={}&collection_id={}".format(
        reverse("admin:djangocms_moderation_moderationrequest_resubmit"),
        ",".join(selected),
        request._collection.id,
    )
    return HttpResponseRedirect(url)


resubmit_selected.short_description = _("Resubmit changes for review")


def reject_selected(modeladmin, request, queryset):
    """
    Validate and reject all the selected moderation requests and notify
    the author about these requests
    """
    selected = request.POST.getlist(ACTION_CHECKBOX_NAME)
    url = "{}?ids={}&collection_id={}".format(
        reverse("admin:djangocms_moderation_moderationrequest_rework"),
        ",".join(selected),
        request._collection.id,
    )
    return HttpResponseRedirect(url)


reject_selected.short_description = _("Submit for rework")


def approve_selected(modeladmin, request, queryset):
    selected = request.POST.getlist(ACTION_CHECKBOX_NAME)
    url = "{}?ids={}&collection_id={}".format(
        reverse("admin:djangocms_moderation_moderationrequest_approve"),
        ",".join(selected),
        request._collection.id,
    )
    return HttpResponseRedirect(url)


approve_selected.short_description = _("Approve")


def delete_selected(modeladmin, request, queryset):
    if not modeladmin.has_delete_permission(request):
        raise PermissionDenied

    selected = request.POST.getlist(ACTION_CHECKBOX_NAME)
    url = "{}?ids={}&collection_id={}".format(
        reverse('admin:djangocms_moderation_moderationrequesttreenode_delete'),
        ",".join(selected),
        request._collection.id,
    )
    return HttpResponseRedirect(url)


delete_selected.short_description = _("Remove selected")
delete_selected.__name__ = 'remove_selected'


def publish_selected(modeladmin, request, queryset):
    if request.user != request._collection.author:
        raise PermissionDenied

    selected = request.POST.getlist(ACTION_CHECKBOX_NAME)
    url = "{}?ids={}&collection_id={}".format(
        reverse("admin:djangocms_moderation_moderationrequest_publish"),
        ",".join(selected),
        request._collection.id,
    )
    return HttpResponseRedirect(url)


publish_selected.short_description = _("Publish selected requests")


def convert_queryset_to_version_queryset(queryset):
    if not queryset:
        return Version.objects.none()

    id_map = defaultdict(list)
    for obj in queryset:
        model = getattr(obj, "model", None)
        if model is None:
            model = obj._meta.model

        from django.db.models.base import Model, ModelBase

        model_bases = [ModelBase, Model]
        if hasattr(model, "polymorphic_ctype_id"):
            from polymorphic.base import PolymorphicModelBase

            model_bases.append(PolymorphicModelBase)
        model = next(
            m
            for m in reversed(model.mro())
            if (
                isinstance(m, tuple(model_bases))
                and m not in model_bases
                and not m._meta.abstract
            )
        )

        id_map[model].append(obj.pk)
    q = Q()
    for obj_model, ids in id_map.items():
        ctype = ContentType.objects.get_for_model(obj_model).pk
        q |= Q(content_type_id=ctype, object_id__in=ids)
    return Version.objects.filter(q)


def add_items_to_collection(modeladmin, request, queryset):
    """Action to add queryset to moderation collection."""
    version_ids = convert_queryset_to_version_queryset(queryset).values_list(
        "pk", flat=True
    )
    version_ids = [str(x) for x in version_ids]
    if version_ids:
        admin_url = add_url_parameters(
            get_admin_url(
                name="cms_moderation_items_to_collection",
                language=request.GET.get("language"),
                args=(),
            ),
            version_ids=",".join(version_ids),
            return_to_url=request.headers.get("referer", ""),
        )
        return HttpResponseRedirect(admin_url)
    else:
        modeladmin.message_user(
            request, _("No suitable items found to add to moderation collection")
        )
        return HttpResponseRedirect(request.headers.get("referer", ""))


add_items_to_collection.short_description = _("Add to moderation collection")

add_item_to_unpublish_collection = partial(add_items_to_collection)
add_item_to_unpublish_collection.__name__ = 'add_item_to_unpublish_collection'
add_item_to_unpublish_collection.short_description = _('Add items to a collection to unpublish')


def post_bulk_actions(collection):
    if collection.should_be_archived():
        collection.status = constants.ARCHIVED
        collection.save(update_fields=["status"])


def publish_version(version, user):
    try:
        version.publish(user)
    except TransitionNotAllowed:
        return False
    return True
