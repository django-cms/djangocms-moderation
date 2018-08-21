from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.utils.translation import ugettext, ugettext_lazy as _, ungettext


def publish_selected(modeladmin, request, queryset):
    if request.user != modeladmin.collection.author:
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
    