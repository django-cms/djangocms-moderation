import json

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.urls import reverse
from django.utils.functional import cached_property
from django.utils.translation import gettext, gettext_lazy as _

from cms.models.fields import PlaceholderField

from djangocms_versioning.models import Version
from treebeard.mp_tree import MP_Node

from .emails import notify_collection_moderators
from .managers import CollectionManager
from .utils import generate_compliance_number


from . import conf, constants, signals  # isort:skip


try:
    from djangocms_versioning.helpers import version_is_locked

    def version_is_unlocked_for_moderation(version, user):
        return version_is_locked(version) is None
except ImportError:
    def version_is_unlocked_for_moderation(version, user):
        return version.created_by == user


class ConfirmationPage(models.Model):
    CONTENT_TYPES = (
        (constants.CONTENT_TYPE_PLAIN, _("Plain")),
        (constants.CONTENT_TYPE_FORM, _("Form")),
    )

    name = models.CharField(verbose_name=_("name"), max_length=50)
    content = PlaceholderField("confirmation_content")
    content_type = models.CharField(
        verbose_name=_("Content Type"),
        choices=CONTENT_TYPES,
        default=constants.CONTENT_TYPE_FORM,
        max_length=50,
    )
    template = models.CharField(
        verbose_name=_("Template"),
        choices=conf.CONFIRMATION_PAGE_TEMPLATES,
        default=conf.DEFAULT_CONFIRMATION_PAGE_TEMPLATE,
        max_length=100,
    )

    class Meta:
        verbose_name = _("Confirmation Page")
        verbose_name_plural = _("Confirmation Pages")

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("admin:cms_moderation_confirmation_page", args=(self.pk,))

    def is_valid(self, active_request, for_step, is_reviewed=False):
        from .helpers import get_form_submission_for_step

        submitted_form = get_form_submission_for_step(active_request, for_step)

        if self.content_type == constants.CONTENT_TYPE_FORM and not submitted_form:
            # No form submission for the attached confirmation form
            return False
        elif self.content_type != constants.CONTENT_TYPE_FORM and not is_reviewed:
            # Any other confirmation content type but not yet reviewed
            return False
        return True


class Role(models.Model):
    name = models.CharField(
        verbose_name=_('name'),
        max_length=120,
        unique=True,
    )
    user = models.ForeignKey(
        to=settings.AUTH_USER_MODEL, verbose_name=_("user"), blank=True, null=True, on_delete=models.CASCADE
    )
    group = models.ForeignKey(
        to=Group, verbose_name=_("group"), blank=True, null=True, on_delete=models.CASCADE
    )
    confirmation_page = models.ForeignKey(
        to=ConfirmationPage,
        verbose_name=_("confirmation page"),
        related_name="+",
        blank=True,
        null=True,
        on_delete=models.PROTECT,
    )

    class Meta:
        verbose_name = _("Role")
        verbose_name_plural = _("Roles")

    def __str__(self):
        return self.name

    def clean(self):
        if self.user_id and self.group_id:
            message = gettext("Can't pick both user and group. Only one.")
            raise ValidationError(message)

    def user_is_assigned(self, user):
        if self.user_id:
            return self.user_id == user.pk
        return self.group.user_set.filter(pk=user.pk).exists()

    def get_users_queryset(self):
        if self.user_id:
            return get_user_model().objects.filter(pk=self.user_id)
        return self.group.user_set.all()


class Workflow(models.Model):
    name = models.CharField(verbose_name=_("name"), max_length=120, unique=True)
    is_default = models.BooleanField(verbose_name=_("is default"), default=False)
    identifier = models.CharField(
        verbose_name=_("identifier"),
        max_length=128,
        blank=True,
        default="",
        help_text=_(
            "Identifier is a 'free' field you could use for internal "
            "purposes. For example, it could be used as a workflow "
            "specific prefix of a compliance number"
        ),
    )
    requires_compliance_number = models.BooleanField(
        verbose_name=_("requires compliance number?"),
        default=False,
        help_text=_(
            "Does the Compliance number need to be generated before "
            "the moderation request is approved? Please select the "
            "compliance number backend below"
        ),
    )
    compliance_number_backend = models.CharField(
        verbose_name=_("compliance number backend"),
        choices=conf.COMPLIANCE_NUMBER_BACKENDS,
        max_length=255,
        default=conf.DEFAULT_COMPLIANCE_NUMBER_BACKEND,
    )

    class Meta:
        verbose_name = _("Workflow")
        verbose_name_plural = _("Workflows")
        ordering = ("name",)

    def __str__(self):
        return self.name

    def clean(self):
        if not self.is_default:
            return

        workflows = Workflow.objects.filter(is_default=True)

        if self.pk:
            workflows = workflows.exclude(pk=self.pk)

        if workflows.exists():
            message = gettext("Can't have two default workflows, only one is allowed.")
            raise ValidationError(message)

    @cached_property
    def first_step(self):
        return self.steps.first()


class WorkflowStep(models.Model):
    role = models.ForeignKey(
        to=Role, verbose_name=_("role"), on_delete=models.CASCADE
    )
    is_required = models.BooleanField(verbose_name=_("is mandatory"), default=True)
    workflow = models.ForeignKey(
        to=Workflow,
        verbose_name=_("workflow"),
        related_name="steps",
        on_delete=models.CASCADE
    )
    order = models.PositiveIntegerField()

    class Meta:
        ordering = ("order",)
        unique_together = ("role", "workflow")
        verbose_name = _("Step")
        verbose_name_plural = _("Steps")

    def __str__(self):
        return self.role.name

    def get_next(self, cache=True, **kwargs):
        if cache and hasattr(self, "_next_step"):
            return self._next_step

        field = self._meta.get_field("order")

        try:
            self._next_step = self._get_next_or_previous_by_FIELD(
                field=field, is_next=True, workflow=self.workflow, **kwargs
            )
        except WorkflowStep.DoesNotExist:
            self._next_step = None
        return self._next_step

    def get_next_required(self):
        return self.get_next(cache=False, is_required=True)


class ModerationCollection(models.Model):
    name = models.CharField(verbose_name=_("collection name"), max_length=128)
    author = models.ForeignKey(
        to=settings.AUTH_USER_MODEL,
        verbose_name=_("moderator"),
        on_delete=models.CASCADE,
    )
    workflow = models.ForeignKey(
        to=Workflow, verbose_name=_("workflow"), related_name="moderation_collections",
        on_delete=models.CASCADE
    )
    status = models.CharField(
        max_length=10,
        choices=constants.STATUS_CHOICES,
        default=constants.COLLECTING,
        db_index=True,
    )
    date_created = models.DateTimeField(auto_now_add=True)
    date_modified = models.DateTimeField(auto_now=True)

    objects = CollectionManager()

    class Meta:
        verbose_name = _("collection")
        permissions = (
            ("can_change_author", _("Can change collection author")),
            ("cancel_moderationcollection", _("Can cancel collection")),
        )

    def __str__(self):
        return self.name

    @property
    def job_id(self):
        return f"{self.pk}"

    @property
    def author_name(self):
        return self.author.get_full_name() or self.author.get_username()

    @property
    def reviewers(self):
        """
        DEPRECATED - if you need to get a list of reviewers use the following instead
        obj = ModerationCollection.objects.all().prefetch_reviewers().first()
        reviewers = ModerationCollection.objects.reviewers(obj)

        The above method makes sure that you won't incur a query overhead
        """
        reviewers = self.objects.reviewers(self)
        return ", ".join(map(get_user_model().get_full_name, reviewers))

    def allow_submit_for_review(self, user):
        """
        Can this collection be submitted for review?
        :return: <bool>
        """
        return all(
            [
                self.author == user,
                self.status == constants.COLLECTING,
                self.moderation_requests.exists(),
            ]
        )

    def submit_for_review(self, by_user, to_user=None):
        """
        Submit all the moderation requests belonging to this collection for
        review and mark the collection as locked
        """
        for moderation_request in self.moderation_requests.all():
            action = moderation_request.actions.create(
                by_user=by_user, to_user=to_user, action=constants.ACTION_STARTED
            )
        # Lock the collection as it has been now submitted for moderation
        self.status = constants.IN_REVIEW
        self.save(update_fields=["status"])
        # It is fine to pass any `action` from any moderation_request.actions
        # above as it will have the same moderators
        notify_collection_moderators(
            collection=self,
            moderation_requests=self.moderation_requests.all(),
            action_obj=action,
        )
        signals.submitted_for_review.send(
            sender=self.__class__,
            collection=self,
            moderation_requests=list(self.moderation_requests.all()),
            user=by_user,
            rework=False,
        )

    def is_cancellable(self, user):
        return all(
            [
                self.author == user,
                self.status not in (constants.ARCHIVED, constants.CANCELLED),
                self.author.has_perm('djangocms_moderation.cancel_moderationcollection')
            ]
        )

    def cancel(self, user):
        """
        Cancel all active moderation requests in this collection
        """
        for moderation_request in self.moderation_requests.filter(is_active=True):
            moderation_request.update_status(
                action=constants.ACTION_CANCELLED,
                by_user=user,
                message=_("Cancelled collection"),
            )
        self.status = constants.CANCELLED
        self.save(update_fields=["status"])

    def should_be_archived(self):
        """
        Collection should be archived if all moderation requests are moderated
        :return: <bool>
        """
        if self.status in [constants.COLLECTING, constants.ARCHIVED]:
            return False
        # TODO this is not efficient, is there a better way?
        for mr in self.moderation_requests.all():
            if not mr.is_approved():
                return False
        return True

    def add_version(self, version, parent=None, include_children=False):
        """
        Add version to the ModerationRequest in this collection.
        Requires validation from .forms.CollectionItemForm
        :return: <ModerationRequest>
        """
        added_items = 0
        moderation_request, created = self.moderation_requests.get_or_create(
            version=version, collection=self, author=self.author
        )
        if created:
            added_items += 1

        # if no parent and a root node with that moderation request
        # doesn't exist, it should be created
        create_root_node = (
            parent is None and
            not ModerationRequestTreeNode.get_root_nodes().filter(moderation_request=moderation_request).exists()
        )
        # if parent passed and a child node with that moderation request
        # doesn't exist under the parent, it should be created
        create_child_node = (
            parent is not None and
            not parent.get_children().filter(moderation_request=moderation_request).exists()
        )
        node = ModerationRequestTreeNode(moderation_request=moderation_request)
        if create_root_node:
            ModerationRequestTreeNode.add_root(instance=node)
        elif create_child_node:
            parent.add_child(instance=node)

        if include_children:
            added_items += self._add_nested_children(version, node)

        return moderation_request, added_items

    def _add_nested_children(self, version, parent_node):
        """Helper method which finds moderated children and adds them to the collection"""
        from .helpers import get_moderated_children_from_placeholder

        parent = version.content
        added_items = 0
        if not getattr(parent, "get_placeholders", None):
            return added_items
        for placeholder in parent.get_placeholders():
            for child_version in get_moderated_children_from_placeholder(
                placeholder, version.versionable.grouping_values(parent)
            ):
                # Don't add the version if it's already part of the collection or locked by another user
                if version_is_unlocked_for_moderation(child_version, version.created_by):
                    moderation_request, _added_items = self.add_version(
                        child_version, parent=parent_node, include_children=True
                    )
                else:
                    _added_items = self._add_nested_children(child_version, parent_node)
                added_items += _added_items
        return added_items


class ModerationRequestTreeNode(MP_Node):
    moderation_request = models.ForeignKey(
        to='ModerationRequest',
        verbose_name=_('moderation_request'),
        on_delete=models.CASCADE,
    )

    class Meta:
        ordering = ('id',)

    def __str__(self):
        return str(self.id)


class ModerationRequest(models.Model):
    collection = models.ForeignKey(
        to=ModerationCollection,
        related_name="moderation_requests",
        on_delete=models.CASCADE,
    )
    version = models.ForeignKey(
        to=Version, verbose_name=_("version"), on_delete=models.CASCADE
    )
    language = models.CharField(
        verbose_name=_("language"), max_length=20, choices=settings.LANGUAGES
    )
    is_active = models.BooleanField(
        verbose_name=_("is active"), default=True, db_index=True
    )
    date_sent = models.DateTimeField(verbose_name=_("date sent"), auto_now_add=True)
    compliance_number = models.CharField(
        verbose_name=_("compliance number"),
        max_length=32,
        blank=True,
        null=True,
        unique=True,
        editable=False,
    )
    author = models.ForeignKey(
        to=settings.AUTH_USER_MODEL,
        verbose_name=_("author"),
        related_name="+",
        on_delete=models.CASCADE,
    )

    class Meta:
        verbose_name = _("Request")
        verbose_name_plural = _("Requests")
        unique_together = ("collection", "version")
        ordering = ["id"]

    def __str__(self):
        return f"{self.pk} {self.version_id}"

    @cached_property
    def workflow(self):
        return self.collection.workflow

    def has_pending_step(self):
        return self.get_pending_steps().exists()

    def has_required_pending_steps(self):
        return self.get_pending_required_steps().exists()

    def is_approved(self):
        return self.is_active and not self.has_required_pending_steps()

    def version_can_be_published(self):
        return self.is_approved() and self.version.can_be_published()

    def is_rejected(self):
        last_action = self.get_last_action()
        return last_action and last_action.action == constants.ACTION_REJECTED

    @transaction.atomic
    def update_status(self, action, by_user, message="", to_user=None):
        is_approved = action == constants.ACTION_APPROVED
        is_rejected = action == constants.ACTION_REJECTED

        if is_approved:
            step_approved = self.user_get_step(by_user)
        else:
            step_approved = None

        if is_rejected:
            # This workflow is now rejected, so it needs to be resubmitted by
            # the content author, so lets mark all the actions taken
            # so far as archived. They need to be re-taken
            self.actions.all().update(is_archived=True)

        # If request is Rejected or Resubmitted, it still counts as active
        # as rejected means it is submitted back to the content author
        # to make the changes
        self.is_active = action in (
            constants.ACTION_APPROVED,
            constants.ACTION_REJECTED,
            constants.ACTION_RESUBMITTED,
        )
        self.save(update_fields=["is_active"])

        self.actions.create(
            by_user=by_user,
            to_user=to_user,
            action=action,
            message=message,
            step_approved=step_approved,
        )

        if self.should_set_compliance_number():
            self.set_compliance_number()

    def should_set_compliance_number(self):
        """
        Certain workflows need to generate a compliance number under some
        circumstances.
        Lets check for that here
        """
        return all(
            [
                self.workflow.requires_compliance_number,
                not self.compliance_number,
                self.is_approved(),
            ]
        )

    def get_first_action(self):
        return self.actions.first()

    def get_last_action(self):
        return self.actions.last()

    def get_pending_steps(self):
        steps_approved = self.actions.filter(
            step_approved__isnull=False, is_archived=False
        ).values_list("step_approved__pk", flat=True)
        return self.workflow.steps.exclude(pk__in=steps_approved)

    def get_pending_required_steps(self):
        return self.get_pending_steps().filter(is_required=True)

    def get_next_required(self):
        return self.get_pending_required_steps().first()

    def user_get_step(self, user):
        for step in self.get_pending_steps().select_related("role"):
            if step.role.user_is_assigned(user):
                return step
        return None

    def user_can_resubmit(self, user):
        """
        Lets workout if the user can edit and then resubmit the content for
        moderation again. This might happen if the moderation request was
        rejected by the moderator and submitted back to the content author
        for amends
        """
        return self.author == user and self.is_rejected()

    def user_can_take_moderation_action(self, user):
        """
        Can this user approve or reject the moderation request
        for the current step?
        """
        if self.is_rejected():
            # If the last action was a rejection, no one can approve or
            # reject the current action (content author can now act on the
            # feedback and resubmit the edits for moderation)
            return False

        pending_steps = self.get_pending_steps().select_related("role")
        for step in pending_steps.iterator():
            is_assigned = step.role.user_is_assigned(user)

            if step.is_required and not is_assigned:
                return False
            elif is_assigned:
                return True
        return False

    def user_can_moderate(self, user):
        """
        Is `user` involved in the moderation process at some point?
        """
        for step in self.workflow.steps.select_related("role__group"):
            if step.role.user_is_assigned(user):
                return True
        return False

    def user_is_author(self, user):
        return user == self.author

    def user_can_view_comments(self, user):
        return self.user_is_author(user) or self.user_can_moderate(user)

    def set_compliance_number(self):
        self.compliance_number = generate_compliance_number(
            self.workflow.compliance_number_backend, moderation_request=self
        )
        self.save(update_fields=["compliance_number"])


class ModerationRequestAction(models.Model):
    action = models.CharField(
        verbose_name=_("status"), max_length=30, choices=constants.ACTION_CHOICES
    )
    # User who created this action
    by_user = models.ForeignKey(
        to=settings.AUTH_USER_MODEL,
        verbose_name=_("by user"),
        related_name="+",
        on_delete=models.CASCADE,
    )
    to_user = models.ForeignKey(
        to=settings.AUTH_USER_MODEL,
        verbose_name=_("to user"),
        blank=True,
        null=True,
        on_delete=models.CASCADE,
    )
    # Role which is next in the moderation flow
    to_role = models.ForeignKey(
        to=Role,
        verbose_name=_("to role"),
        blank=True,
        null=True,
        related_name="+",
        on_delete=models.CASCADE,
    )

    # This is the step which approved the moderation request
    step_approved = models.ForeignKey(
        to=WorkflowStep,
        verbose_name=_("step approved"),
        blank=True,
        null=True,
        on_delete=models.CASCADE,
    )
    message = models.TextField(verbose_name=_("message"), blank=True)
    moderation_request = models.ForeignKey(
        to=ModerationRequest,
        verbose_name=_("moderation_request"),
        related_name="actions",
        on_delete=models.CASCADE
    )

    date_taken = models.DateTimeField(verbose_name=_("date taken"), auto_now_add=True)

    # Action can become "archived" if the moderation request has been rejected
    # and re-assigned to the content author for their resubmission.
    # In this scenario, all the actions have to be retaken, so we mark the
    # existing ones as "archived"
    is_archived = models.BooleanField(default=False)

    class Meta:
        ordering = ("date_taken",)
        verbose_name = _("Action")
        verbose_name_plural = _("Actions")

    def __str__(self):
        return f"{self.moderation_request_id} - {self.get_action_display()}"

    def get_by_user_name(self):
        if not self.to_user:
            return ""
        return self._get_user_name(self.by_user)

    def get_to_user_name(self):
        if not self.to_user:
            return ""
        return self._get_user_name(self.to_user)

    def _get_user_name(self, user):
        return user.get_full_name() or user.get_username()

    def save(self, **kwargs):
        """
        The point of this is to workout the "to Role",
        so we know which role will be approving the request next, if any
        """

        # If we are rejecting, then we don't need to workout the `to_role`,
        # as only the content author will amend and resubmit the changes
        if self.action == constants.ACTION_REJECTED:
            next_step = None
        elif self.to_user:
            next_step = self.moderation_request.user_get_step(self.to_user)
        elif self.action in (constants.ACTION_STARTED, constants.ACTION_RESUBMITTED):
            next_step = self.moderation_request.workflow.first_step
        else:
            current_step = self.moderation_request.user_get_step(self.by_user)
            next_step = current_step.get_next() if current_step else None

        if next_step:
            self.to_role_id = next_step.role_id
        super().save(**kwargs)


class AbstractComment(models.Model):
    message = models.TextField(blank=True, verbose_name=_("message"))
    author = models.ForeignKey(
        to=settings.AUTH_USER_MODEL, verbose_name=_("author"), on_delete=models.CASCADE
    )
    date_created = models.DateTimeField(auto_now_add=True)

    class Meta:
        abstract = True

    @property
    def author_name(self):
        return self.author.get_full_name() or self.author.get_username()


class CollectionComment(AbstractComment):
    collection = models.ForeignKey(to=ModerationCollection, on_delete=models.CASCADE)


class RequestComment(AbstractComment):
    moderation_request = models.ForeignKey(
        to=ModerationRequest, on_delete=models.CASCADE
    )


class ConfirmationFormSubmission(models.Model):
    moderation_request = models.ForeignKey(
        to=ModerationRequest,
        verbose_name=_("moderation request"),
        related_name="form_submissions",
        on_delete=models.CASCADE,
    )
    for_step = models.ForeignKey(
        to=WorkflowStep,
        verbose_name=_("for step"),
        related_name="+",
        on_delete=models.CASCADE,
    )
    by_user = models.ForeignKey(
        to=settings.AUTH_USER_MODEL,
        verbose_name=_("by user"),
        related_name="+",
        on_delete=models.CASCADE,
    )
    data = models.TextField(blank=True, editable=False)
    submitted_at = models.DateTimeField(auto_now_add=True)
    confirmation_page = models.ForeignKey(
        to=ConfirmationPage,
        verbose_name=_("confirmation page"),
        related_name="+",
        on_delete=models.PROTECT,
    )

    def __str__(self):
        return f"{self.request_id} - {self.for_step}"

    class Meta:
        verbose_name = _("Confirmation Form Submission")
        verbose_name_plural = _("Confirmation Form Submissions")
        unique_together = ("moderation_request", "for_step")

    def get_by_user_name(self):
        user = self.by_user
        return user.get_full_name() or getattr(user, user.USERNAME_FIELD)

    def get_form_data(self):
        return json.loads(self.data)
