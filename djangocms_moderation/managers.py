from __future__ import unicode_literals

from django.db.models import Manager, Q

from .constants import (
    ACCESS_CHILDREN,
    ACCESS_DESCENDANTS,
    ACCESS_PAGE,
    ACCESS_PAGE_AND_CHILDREN,
    ACCESS_PAGE_AND_DESCENDANTS,
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
            Q(grant_on=ACCESS_PAGE_AND_DESCENDANTS)
            | Q(grant_on=ACCESS_PAGE_AND_CHILDREN)
            | Q(grant_on=ACCESS_PAGE)
        )
        return self.filter(query).order_by("-extended_object__node__depth").first()
