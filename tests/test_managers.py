from djangocms_moderation.models import ModerationCollection

from .utils.base import BaseTestCase


class CollectionManangerTest(BaseTestCase):

    def test_reviewers_wont_execute_too_many_queries(self):
        """This works as a stop gap that will prevent any further changes to
        execute more than 9 queries for prefetching_reviweers"""
        with self.assertNumQueries(9):
            colls = ModerationCollection.objects.all().prefetch_reviewers()
            for collection in colls:
                ModerationCollection.objects.reviewers(collection)
