from django.db import models
from django.db.models import Manager, Q

from .constants import (
    ACCESS_CHILDREN,
    ACCESS_DESCENDANTS,
    ACCESS_PAGE,
    ACCESS_PAGE_AND_CHILDREN,
    ACCESS_PAGE_AND_DESCENDANTS,
    COLLECTING,
)


class PageModerationManager(Manager):
    def for_page(self, page):
        """Returns queryset containing all instances somehow connected to given
        page. This includes permissions to page itself and permissions inherited
        from higher pages.
        """
        page = page.get_draft_object()
        node = page.node
        paths = node.get_ancestor_paths()
        # Ancestors
        query = Q(extended_object__node__path__in=paths) & (
            Q(grant_on=ACCESS_DESCENDANTS) | Q(grant_on=ACCESS_PAGE_AND_DESCENDANTS)
        )

        if page.parent_page:
            # Direct parent
            query |= Q(extended_object__pk=page.parent_page.pk) & (
                Q(grant_on=ACCESS_CHILDREN) | Q(grant_on=ACCESS_PAGE_AND_CHILDREN)
            )

        query |= Q(extended_object=page) & (
            Q(grant_on=ACCESS_PAGE_AND_DESCENDANTS) |
            Q(grant_on=ACCESS_PAGE_AND_CHILDREN) |
            Q(grant_on=ACCESS_PAGE)
        )
        return self.filter(query).order_by("-extended_object__node__depth").first()


class CollectionQuerySet(models.QuerySet):
    def prefetch_reviewers(self):
        """
        Prefetch all necessary relations so it's possible to get reviewers
        without incurring extra queries.
        """
        return self.prefetch_related(
            'moderation_requests',
            'moderation_requests__actions',
            'moderation_requests__actions__to_user',
            'workflow__steps__role__group__user_set'
        )


class CollectionManager(Manager):

    def get_queryset(self):
        return CollectionQuerySet(self.model, using=self._db)

    def reviewers(self, collection):
        """
        Returns a set of all reviewers assigned to any ModerationRequestAction
        associated with this collection. If none are associated with a given
        action then get the role for the step in the workflow and include all
        reviewers within that list.

        Please note that if collection has not been prefetched using
        `prefetch_reviewers` this has a chance of making a massive overhead.
        """

        reviewers = set()
        moderation_requests = collection.moderation_requests.all()
        for mr in moderation_requests:
            moderation_request_actions = mr.actions.all()
            reviewers_in_actions = set()
            for mra in moderation_request_actions:
                if mra.to_user:
                    reviewers_in_actions.add(mra.to_user)
                    reviewers.add(mra.to_user)

            if not reviewers_in_actions and collection.status != COLLECTING:
                role = collection.workflow.first_step.role
                users = role.get_users_queryset()
                for user in users:
                    reviewers.add(user)

        return reviewers
