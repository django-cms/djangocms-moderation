from __future__ import unicode_literals

import json

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.core.urlresolvers import reverse
from django.db import models, transaction
from django.utils.encoding import python_2_unicode_compatible
from django.utils.functional import cached_property
from django.utils.translation import ugettext, ugettext_lazy as _

from cms.extensions import PageExtension
from cms.extensions.extension_pool import extension_pool
from cms.models.fields import PlaceholderField

from .emails import notify_request_author, notify_requested_moderator
from .managers import PageModerationManager
from .utils import generate_reference_number


from . import conf, constants  # isort:skip


@python_2_unicode_compatible
class ConfirmationPage(models.Model):
    CONTENT_TYPES = (
        (constants.CONTENT_TYPE_PLAIN, _('Plain')),
        (constants.CONTENT_TYPE_FORM, _('Form')),
    )

    name = models.CharField(verbose_name=_('name'), max_length=50)
    content = PlaceholderField('confirmation_content')
    content_type = models.CharField(
        verbose_name=_('Content Type'),
        choices=CONTENT_TYPES,
        default=constants.CONTENT_TYPE_FORM,
        max_length=50,
    )
    template = models.CharField(
        verbose_name=_('Template'),
        choices=conf.CONFIRMATION_PAGE_TEMPLATES,
        default=conf.DEFAULT_CONFIRMATION_PAGE_TEMPLATE,
        max_length=100,
    )

    class Meta:
        verbose_name = _('Confirmation Page')
        verbose_name_plural = _('Confirmation Pages')

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('admin:cms_moderation_confirmation_page', args=(self.pk,))

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


@python_2_unicode_compatible
class Role(models.Model):
    name = models.CharField(verbose_name=_('name'), max_length=120)
    user = models.ForeignKey(
        to=settings.AUTH_USER_MODEL,
        verbose_name=_('user'),
        blank=True,
        null=True,
    )
    group = models.ForeignKey(
        to=Group,
        verbose_name=_('group'),
        blank=True,
        null=True,
    )
    confirmation_page = models.ForeignKey(
        to=ConfirmationPage,
        verbose_name=_('confirmation page'),
        related_name='+',
        blank=True,
        null=True,
        on_delete=models.PROTECT,
    )

    class Meta:
        verbose_name = _('Role')
        verbose_name_plural = _('Roles')

    def __str__(self):
        return self.name

    def clean(self):
        if self.user_id and self.group_id:
            message = ugettext('Can\'t pick both user and group. Only one.')
            raise ValidationError(message)

    def user_is_assigned(self, user):
        if self.user_id:
            return self.user_id == user.pk
        return self.group.user_set.filter(pk=user.pk).exists()

    def get_users_queryset(self):
        if self.user_id:
            return get_user_model().objects.filter(pk=self.user_id)
        return self.group.user_set.all()


@python_2_unicode_compatible
class Workflow(models.Model):
    name = models.CharField(
        verbose_name=_('name'),
        max_length=120,
        unique=True,
    )
    is_default = models.BooleanField(
        verbose_name=_('is default'),
        default=False,
    )
    reference_number_backend = models.CharField(
        choices=conf.REFERENCE_NUMBER_BACKENDS,
        max_length=255,
        default=conf.DEFAULT_REFERENCE_NUMBER_BACKEND,
    )

    class Meta:
        verbose_name = _('Workflow')
        verbose_name_plural = _('Workflows')

    def __str__(self):
        return self.name

    def clean(self):
        if not self.is_default:
            return

        workflows = Workflow.objects.filter(is_default=True)

        if self.pk:
            workflows = workflows.exclude(pk=self.pk)

        if workflows.exists():
            message = ugettext('Can\'t have two default workflows, only one is allowed.')
            raise ValidationError(message)

    @cached_property
    def first_step(self):
        return self.steps.first()

    def _lookup_active_request(self, page, language):
        lookup = (
            self
            .requests
            .filter(
                page=page,
                language=language,
                is_active=True,
            )
        )
        return lookup

    def get_active_request(self, page, language):
        lookup = self._lookup_active_request(page, language)

        try:
            active_request = lookup.get()
        except PageModerationRequest.DoesNotExist:
            active_request = None
        return active_request

    def has_active_request(self, page, language):
        lookup = self._lookup_active_request(page, language)
        return lookup.exists()

    @transaction.atomic
    def submit_new_request(self, by_user, page, language, message='', to_user=None):
        request = self.requests.create(
            page=page,
            language=language,
            is_active=True,
            workflow=self,
        )
        new_action = request.actions.create(
            by_user=by_user,
            to_user=to_user,
            action=constants.ACTION_STARTED,
            message=message,
        )
        notify_requested_moderator(request, new_action)
        return request


@python_2_unicode_compatible
class WorkflowStep(models.Model):
    role = models.ForeignKey(
        to=Role,
        verbose_name=_('role'),
        related_name='+',
    )
    is_required = models.BooleanField(
        verbose_name=_('is mandatory'),
        default=True,
    )
    workflow = models.ForeignKey(
        to=Workflow,
        verbose_name=_('workflow'),
        related_name='steps',
    )
    order = models.PositiveIntegerField()

    class Meta:
        ordering = ('order',)
        unique_together = ('role', 'workflow')
        verbose_name = _('Step')
        verbose_name_plural = _('Steps')

    def __str__(self):
        return self.role.name

    def get_next(self, cache=True, **kwargs):
        if cache and hasattr(self, '_next_step'):
            return self._next_step

        field = self._meta.get_field('order')

        try:
            self._next_step = self._get_next_or_previous_by_FIELD(
                field=field,
                is_next=True,
                workflow=self.workflow,
                **kwargs
            )
        except WorkflowStep.DoesNotExist:
            self._next_step = None
        return self._next_step

    def get_next_required(self):
        return self.get_next(cache=False, is_required=True)


@python_2_unicode_compatible
class PageModeration(PageExtension):
    ACCESS_CHOICES = (
        (constants.ACCESS_PAGE, _('Current page')),
        (constants.ACCESS_CHILDREN, _('Page children (immediate)')),
        (constants.ACCESS_PAGE_AND_CHILDREN, _('Page and children (immediate)')),
        (constants.ACCESS_DESCENDANTS, _('Page descendants')),
        (constants.ACCESS_PAGE_AND_DESCENDANTS, _('Page and descendants')),
    )

    workflow = models.ForeignKey(
        to=Workflow,
        verbose_name=_('workflow'),
        related_name='+',
    )
    grant_on = models.IntegerField(
        verbose_name=_('grant on'),
        choices=ACCESS_CHOICES,
        default=constants.ACCESS_PAGE_AND_DESCENDANTS,
    )
    enabled = models.BooleanField(
        verbose_name=_('enable moderation for page'),
        default=True,
    )

    objects = PageModerationManager()

    def __str__(self):
        return self.extended_object.get_page_title()

    @cached_property
    def page(self):
        return self.get_page()

    def copy_relations(self, oldinstance, language):
        self.workflow_id = oldinstance.workflow_id


@python_2_unicode_compatible
class PageModerationRequest(models.Model):
    page = models.ForeignKey(
        to='cms.Page',
        verbose_name=_('page'),
        limit_choices_to={
            'is_page_type': False,
            'publisher_is_draft': True,
        },
    )
    language = models.CharField(
        verbose_name=_('language'),
        max_length=5,
        choices=settings.LANGUAGES,
    )
    workflow = models.ForeignKey(
        to=Workflow,
        verbose_name=_('workflow'),
        related_name='requests',
    )
    is_active = models.BooleanField(
        default=False,
        db_index=True,
    )
    date_sent = models.DateTimeField(
        verbose_name=_('date sent'),
        auto_now_add=True,
    )
    reference_number = models.CharField(
        max_length=32,
        null=True,
        unique=True,
    )

    class Meta:
        verbose_name = _('Request')
        verbose_name_plural = _('Requests')

    def __str__(self):
        return "{} {}".format(
            self.pk,
            self.page.get_page_title(self.language)
        )

    @cached_property
    def author(self):
        """
        Author of this request is the user who created the first action
        """
        return self.get_first_action().by_user

    @cached_property
    def has_pending_step(self):
        return self.get_pending_steps().exists()

    @cached_property
    def has_required_pending_steps(self):
        return self.get_pending_required_steps().exists()

    @cached_property
    def is_approved(self):
        return self.is_active and not self.has_required_pending_steps

    @cached_property
    def is_rejected(self):
        return self.get_last_action().action == constants.ACTION_REJECTED

    @transaction.atomic
    def update_status(self, action, by_user, message='', to_user=None):
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
        self.save(update_fields=['is_active'])

        new_action = self.actions.create(
            by_user=by_user,
            to_user=to_user,
            action=action,
            message=message,
            step_approved=step_approved,
        )

        if new_action.to_user_id or new_action.to_role_id:
            notify_requested_moderator(self, new_action)
        notify_request_author(self, new_action)

    def get_first_action(self):
        return self.actions.first()

    def get_last_action(self):
        return self.actions.last()

    def get_pending_steps(self):
        steps_approved = (
            self
            .actions
            .filter(step_approved__isnull=False, is_archived=False)
            .values_list('step_approved__pk', flat=True)
        )
        return self.workflow.steps.exclude(pk__in=steps_approved)

    def get_pending_required_steps(self):
        return self.get_pending_steps().filter(is_required=True)

    def get_next_required(self):
        return self.get_pending_required_steps().first()

    def user_get_step(self, user):
        for step in self.get_pending_steps().select_related('role'):
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
        return self.author == user and self.is_rejected

    def user_can_take_moderation_action(self, user):
        """
        Can this user approve or reject the moderation request
        for the current step?
        """
        if self.is_rejected:
            # If the last action was a rejection, no one can approve or
            # reject the current action (content author can now act on the
            # feedback and resubmit the edits for moderation)
            return False

        pending_steps = self.get_pending_steps().select_related('role')

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
        for step in self.workflow.steps.select_related('role__group'):
            if step.role.user_is_assigned(user):
                return True
        return False

    def user_is_author(self, user):
        return user == self.get_first_action().by_user

    def user_can_view_comments(self, user):
        return self.user_is_author(user) or self.user_can_moderate(user)

    def set_reference_number(self):
        self.reference_number = generate_reference_number(
            self.workflow.reference_number_backend,
            moderation_request=self,
        )
        self.save(update_fields=['reference_number'])


@python_2_unicode_compatible
class PageModerationRequestAction(models.Model):
    action = models.CharField(
        verbose_name=_('status'),
        max_length=30,
        choices=constants.ACTION_CHOICES,
    )
    # User who created this action
    by_user = models.ForeignKey(
        to=settings.AUTH_USER_MODEL,
        verbose_name=_('by user'),
        related_name='+',
        on_delete=models.CASCADE,
    )
    to_user = models.ForeignKey(
        to=settings.AUTH_USER_MODEL,
        verbose_name=_('to user'),
        blank=True,
        null=True,
        related_name='+',
        on_delete=models.CASCADE,
    )
    # Role which is next in the moderation flow
    to_role = models.ForeignKey(
        to=Role,
        verbose_name=_('to role'),
        blank=True,
        null=True,
        related_name='+',
        on_delete=models.CASCADE,
    )

    # This is the step which approved the moderation request
    step_approved = models.ForeignKey(
        to=WorkflowStep,
        verbose_name=_('step approved'),
        blank=True,
        null=True,
        on_delete=models.CASCADE,
    )
    message = models.TextField(
        verbose_name=_('message'),
        blank=True,
    )
    request = models.ForeignKey(
        to=PageModerationRequest,
        verbose_name=_('request'),
        related_name='actions',
    )
    date_taken = models.DateTimeField(
        verbose_name=_('date taken'),
        auto_now_add=True,
    )

    # Action can become "archived" if the moderation request has been rejected
    # and re-assigned to the content author for their resubmission.
    # In this scenario, all the actions have to be retaken, so we mark the
    # existing ones as "archived"
    is_archived = models.BooleanField(default=False)

    class Meta:
        ordering = ('date_taken',)
        verbose_name = _('Action')
        verbose_name_plural = _('Actions')

    def __str__(self):
        return "{} - {}".format(
            self.request_id, self.get_action_display()
        )

    def get_by_user_name(self):
        return self._get_user_name(self.by_user)

    def get_to_user_name(self):
        return self._get_user_name(self.to_user)

    def _get_user_name(self, user):
        return user.get_full_name() or getattr(user, user.USERNAME_FIELD)

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
            next_step = self.request.user_get_step(self.to_user)
        elif self.action in (constants.ACTION_STARTED, constants.ACTION_RESUBMITTED):
            next_step = self.request.workflow.first_step
        else:
            current_step = self.request.user_get_step(self.by_user)
            next_step = current_step.get_next() if current_step else None

        if next_step:
            self.to_role_id = next_step.role_id
        super(PageModerationRequestAction, self).save(**kwargs)


class ConfirmationFormSubmission(models.Model):
    request = models.ForeignKey(
        to=PageModerationRequest,
        verbose_name=_('request'),
        related_name='form_submissions',
        on_delete=models.CASCADE,
    )
    for_step = models.ForeignKey(
        to=WorkflowStep,
        verbose_name=_('for step'),
        related_name='+',
        on_delete=models.CASCADE,
    )
    by_user = models.ForeignKey(
        to=settings.AUTH_USER_MODEL,
        verbose_name=_('by user'),
        related_name='+',
        on_delete=models.CASCADE,
    )
    data = models.TextField(
        blank=True,
        editable=False,
    )
    submitted_at = models.DateTimeField(auto_now_add=True)
    confirmation_page = models.ForeignKey(
        to=ConfirmationPage,
        verbose_name=_('confirmation page'),
        related_name='+',
        on_delete=models.PROTECT,
    )

    def __str__(self):
        return '{} - {}'.format(self.request_id, self.for_step)

    class Meta:
        verbose_name = _('Confirmation Form Submission')
        verbose_name_plural = _('Confirmation Form Submissions')
        unique_together = ('request', 'for_step')

    def get_by_user_name(self):
        user = self.by_user
        return user.get_full_name() or getattr(user, user.USERNAME_FIELD)

    def get_form_data(self):
        return json.loads(self.data)


extension_pool.register(PageModeration)
