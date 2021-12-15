from django.utils.translation import gettext_lazy as _


# NOTE: those are not just numbers!! we will do binary AND on them,
# so pay attention when adding/changing them, or MASKs..
ACCESS_PAGE = 1
ACCESS_CHILDREN = 2  # just immediate children (1 level)
ACCESS_PAGE_AND_CHILDREN = 3  # just immediate children (1 level)
ACCESS_DESCENDANTS = 4
ACCESS_PAGE_AND_DESCENDANTS = 5

# binary masks for ACCESS permissions
MASK_PAGE = 1
MASK_CHILDREN = 2
MASK_DESCENDANTS = 4

ACCESS_CHOICES = (
    (ACCESS_PAGE, _("Current page")),
    (ACCESS_CHILDREN, _("Page children (immediate)")),
    (ACCESS_PAGE_AND_CHILDREN, _("Page and children (immediate)")),
    (ACCESS_DESCENDANTS, _("Page descendants")),
    (ACCESS_PAGE_AND_DESCENDANTS, _("Page and descendants")),
)

ACTION_RESUBMITTED = "resubmitted"
ACTION_STARTED = "start"
ACTION_REJECTED = "rejected"
ACTION_APPROVED = "approved"
ACTION_CANCELLED = "cancelled"
ACTION_FINISHED = "finished"

ACTION_CHOICES = (
    (ACTION_RESUBMITTED, _("Resubmitted")),
    (ACTION_STARTED, _("Started")),
    (ACTION_REJECTED, _("Rejected")),
    (ACTION_APPROVED, _("Approved")),
    (ACTION_CANCELLED, _("Cancelled")),
    (ACTION_FINISHED, _("Finished")),
)

CONTENT_TYPE_PLAIN = "plain"
CONTENT_TYPE_FORM = "form"

# masks for Collection STATUS
COLLECTING = "COLLECTING"
IN_REVIEW = "IN_REVIEW"
ARCHIVED = "ARCHIVED"
CANCELLED = "CANCELLED"

STATUS_CHOICES = (
    (COLLECTING, _("Collecting")),
    (IN_REVIEW, _("In Review")),
    (ARCHIVED, _("Archived")),
    (CANCELLED, _("Cancelled")),
)
