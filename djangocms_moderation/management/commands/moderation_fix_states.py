from django.core.management.base import BaseCommand

from djangocms_versioning import constants as versioning_constants

from djangocms_moderation import constants as moderation_constants
from djangocms_moderation.models import ModerationRequest


class Command(BaseCommand):
    help = "Repair any ModerationRequest objects that are left in an un-consistent state."

    def add_arguments(self, parser):
        # Named (optional) arguments
        parser.add_argument(
            "--perform-fix",
            action="store_true",
            help="Perform the fix and commit any changes",
        )

    def handle(self, *args, **options):
        self.stdout.write("Running Moderation Fix States command")

        # Find all objects that are left in an inconsistent state
        items = ModerationRequest.objects.filter(
            is_active=True,
            collection__status=moderation_constants.ARCHIVED,
            version__state=versioning_constants.PUBLISHED,
        )

        items_found = items.count()
        if not items_found:
            self.stdout.write(self.style.SUCCESS("No inconsistent ModerationRequest objects found"))
            return

        self.stdout.write(self.style.WARNING("Inconsistent ModerationRequest objects found: %s" % items.count()))
        for request in items:
            self.stdout.write("Found ModerationRequest id: %s" % request.id)

        if not options.get('perform_fix'):
            self.stdout.write(self.style.SUCCESS(
                "Finished without making any changes. To make changes run this command with: --perform-fix"))
            return

        # Perform cleanup operations
        self.stdout.write("Performing cleanup of inconsistent ModerationRequest object states")
        for request in items:
            request.is_active = False
            request.save()
            self.stdout.write("Repaired ModerationRequest id: %s" % request.id)

        self.stdout.write(self.style.SUCCESS("Finished and made the changes successfully."))
