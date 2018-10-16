
from django.contrib import admin
from django.contrib.auth.models import User
from django.utils.translation import ugettext, ugettext_lazy as _

from .models import ModerationCollection, ModerationRequestAction

class ReviewerFilter(admin.SimpleListFilter):
    title = _("By reviewer")
    parameter_name = "reviewer"

    def lookups(self, request, model_admin):
        return User.objects.filter(moderationrequestaction__isnull=False)

    def queryset(self, request, queryset):
        return queryset.filter(moderation_requests__actions__to_user=request.user)
        