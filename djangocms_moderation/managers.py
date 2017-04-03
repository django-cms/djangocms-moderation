from __future__ import unicode_literals

from django.db.models import Manager, Q

from .constants import (
    ACCESS_DESCENDANTS,
    ACCESS_CHILDREN,
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
        paths = [
            page.path[0:pos]
            for pos in range(0, len(page.path), page.steplen)[1:]
        ]
        parents = Q(extended_object__path__in=paths) & (Q(grant_on=ACCESS_DESCENDANTS) | Q(grant_on=ACCESS_PAGE_AND_DESCENDANTS))
        direct_parents = Q(extended_object__pk=page.parent_id) & (Q(grant_on=ACCESS_CHILDREN) | Q(grant_on=ACCESS_PAGE_AND_CHILDREN))
        page_qs = Q(extended_object=page) & (Q(grant_on=ACCESS_PAGE_AND_DESCENDANTS) | Q(grant_on=ACCESS_PAGE_AND_CHILDREN) |
                                  Q(grant_on=ACCESS_PAGE))
        query = (parents | direct_parents | page_qs)
        return self.filter(query).order_by('-extended_object__depth').first()
