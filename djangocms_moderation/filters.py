
from django.contrib import admin
from django.contrib.auth.models import User
from django.utils.encoding import force_text
from django.utils.translation import ugettext_lazy as _


class ReviewerFilter(admin.SimpleListFilter):
    title = _("reviewer")
    parameter_name = "reviewer"
    reviewers = []
    currentuser = {}

    def lookups(self, request, model_admin):
        """
        Provides a reviewers filter if there are any reviewers
        """
        self.currentuser = request.user
        self.reviewers = User.objects.filter(moderationrequestaction__isnull=False).distinct()
        options = []
        for user in self.reviewers:
            options.append((int(user.pk), user.get_full_name() or user.get_username()))
        return options

    def queryset(self, request, queryset):
        if request.GET.get(self.parameter_name):
            return queryset.filter(
                moderation_requests__actions__to_user=request.GET.get(self.parameter_name)
            ).distinct()
        return queryset

    def choices(self, changelist):
        if self.currentuser not in self.reviewers:
            yield {
                'selected': self.value() is None,
                'query_string': changelist.get_query_string({}, [self.parameter_name]),
                'display': _('All'),
            }
        for lookup, title in self.lookup_choices:
            yield {
                'selected': self.value() == force_text(lookup),
                'query_string': changelist.get_query_string({self.parameter_name: lookup}, []),
                'display': title,
            }
