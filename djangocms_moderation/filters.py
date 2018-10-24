
from django.contrib import admin
from django.contrib.auth.models import User
from django.db.models import Q
from django.utils.encoding import force_text
from django.utils.translation import ugettext_lazy as _

from . import constants
from . import helpers


class ModeratorFilter(admin.SimpleListFilter):
    """
    Provides a moderator filter limited to those users who have authored collections
    """
    title = _("moderator")
    parameter_name = "moderator"
    moderators = []

    def lookups(self, request, model_admin):
        options = []
        self.moderators = User.objects.filter(moderationcollection__author__isnull=False).distinct()
        for user in self.moderators:
            options.append((int(user.pk), user.get_full_name() or user.get_username()))
        return options

    def queryset(self, request, queryset):
        if request.GET.get(self.parameter_name):
            return queryset.filter(
                author=request.GET.get(self.parameter_name)
            ).distinct()
        return queryset


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

        # reviewers assigned to review collections by group
        self.reviewers_by_group = helpers.filter_reviewers_by_role_group()

        # reviewers assigned to review collections by role
        self.reviewers_by_role = helpers.filter_reviewers_by_role_user()

        options = []
        # collect all unique users from the three queries
        for user in self.reviewers_by_group:
            options.append((int(user.pk), user.get_full_name() or user.get_username()))
        for user in self.reviewers_by_role:
            if user not in self.reviewers and user not in self.reviewers_by_group:
                options.append((int(user.pk), user.get_full_name() or user.get_username()))
        return options

    def queryset(self, request, queryset):
        if request.GET.get(self.parameter_name):
            result = queryset.filter(
                Q(moderation_requests__actions__to_user=request.GET.get(self.parameter_name)) |
                # also include those that have been assigned to a role, instead of directly to a user
                (
                    # include any direct user assignments to actions
                    Q(moderation_requests__actions__to_user__isnull=True)
                    # exclude status COLLECTING as these will hot have reviewers assigned
                    & ~Q(status=constants.COLLECTING)
                    # include collections with group or role that matches current user
                    & (
                        Q(workflow__steps__role__user=request.GET.get(self.parameter_name)) |
                        Q(workflow__steps__role__group__user=request.GET.get(self.parameter_name))
                    )
                )
            ).distinct()

            return result
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
