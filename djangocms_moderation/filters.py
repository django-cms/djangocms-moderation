
from django.contrib import admin
from django.contrib.auth.models import User


class ReviewerFilter(admin.SimpleListFilter):
    title = _("reviewer")
    parameter_name = "reviewer"

    def lookups(self, request, model_admin):
        """
        Provides a reviewers filter if there are any reviewers
        """
        users = []
        options = []
        for user in User.objects.filter(moderationrequestaction__isnull=False):
            if user in users:
                continue
            else:
                users.append(user)
                options.append((int(user.pk), user.get_full_name() or user.get_username()))
        return options

    def queryset(self, request, queryset):
        if request.GET.get(self.parameter_name):
            return queryset.filter(moderation_requests__actions__to_user=request.GET.get(self.parameter_name))
        return queryset
