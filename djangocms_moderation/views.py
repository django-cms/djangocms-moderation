from __future__ import unicode_literals

from django.contrib import messages
from django.core.urlresolvers import reverse
from django.http import (
    HttpResponseBadRequest,
    HttpResponseForbidden,
    HttpResponseRedirect,
)
from django.shortcuts import get_object_or_404, render
from django.utils.translation import ugettext_lazy as _
from django.views.generic import FormView, ListView

from cms.utils.urlutils import add_url_parameters

from djangocms_moderation.exceptions import CollectionCantBeSubmittedForModeration
from .forms import UpdateModerationRequestForm, SubmitCollectionForModerationForm
from .helpers import (
    get_active_moderation_request,
    get_moderation_workflow,
    get_page_or_404,
)
from .models import (
    ConfirmationFormSubmission,
    ConfirmationPage,
    ModerationRequest,
    ModerationCollection)
from .utils import get_admin_url


from . import constants  # isort:skip


class ModerationRequestView(FormView):

    action = None
    page_title = None
    success_message = None
    template_name = 'djangocms_moderation/request_form.html'
    success_template_name = 'djangocms_moderation/request_finalized.html'

    def dispatch(self, request, *args, **kwargs):
        user = request.user
        self.page_id = args[0]
        self.language = args[1]
        self.page = get_page_or_404(self.page_id, self.language)
        self.workflow = None
        self.active_request = get_active_moderation_request(self.page, self.language)

        if self.active_request:
            self.workflow = self.active_request.workflow

            needs_ongoing = self.action in (constants.ACTION_APPROVED, constants.ACTION_REJECTED)

            if self.action == constants.ACTION_STARTED:
                # Can't start new request if there's one already.
                return HttpResponseBadRequest('Page already has an active moderation request.')
            elif self.active_request.is_approved() and needs_ongoing:
                # Can't reject or approve a moderation request whose steps have all
                # already been approved.
                return HttpResponseBadRequest('Moderation request has already been approved.')
            elif needs_ongoing and not self.active_request.user_can_take_moderation_action(user):
                # User can't approve or reject a request where he's not part of the workflow
                return HttpResponseForbidden('User is not allowed to update request.')
            elif self.action == constants.ACTION_APPROVED:
                next_step = self.active_request.user_get_step(self.request.user)
                confirmation_is_valid = True

                if next_step and next_step.role:
                    confirmation_page_instance = next_step.role.confirmation_page
                else:
                    confirmation_page_instance = None

                if confirmation_page_instance:
                    confirmation_is_valid = confirmation_page_instance.is_valid(
                        active_request=self.active_request,
                        for_step=next_step,
                        is_reviewed=request.GET.get('reviewed'),
                    )

                if not confirmation_is_valid:
                    redirect_url = add_url_parameters(
                        confirmation_page_instance.get_absolute_url(),
                        content_view=True,
                        page=self.page_id,
                        language=self.language,
                    )
                    return HttpResponseRedirect(redirect_url)
        elif self.action != constants.ACTION_STARTED:
            # All except for the new request endpoint require an active moderation request
            return HttpResponseBadRequest('Page does not have an active moderation request.')
        else:
            self.workflow = get_moderation_workflow()

        if not self.workflow:
            return HttpResponseBadRequest('No moderation workflow exists for page.')
        return super(ModerationRequestView, self).dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.save()
        context = self.get_context_data(form=form)
        messages.success(self.request, self.success_message)
        return render(self.request, self.success_template_name, context)

    def get_form_kwargs(self):
        kwargs = super(ModerationRequestView, self).get_form_kwargs()
        kwargs['action'] = self.action
        kwargs['language'] = self.language
        kwargs['page'] = self.page
        kwargs['user'] = self.request.user
        kwargs['workflow'] = self.workflow
        kwargs['active_request'] = self.active_request
        return kwargs

    def get_context_data(self, **kwargs):
        opts = ModerationRequest._meta
        form_submission_opts = ConfirmationFormSubmission._meta

        if self.active_request:
            form_submissions = self.active_request.form_submissions.all()
        else:
            form_submissions = []

        context = super(ModerationRequestView, self).get_context_data(**kwargs)
        context.update({
            'title': self.page_title,
            'has_change_permission': True,
            'opts': opts,
            'root_path': reverse('admin:index'),
            'app_label': opts.app_label,
            'adminform': context['form'],
            'is_popup': True,
            'form_submissions': form_submissions,
            'form_submission_opts': form_submission_opts,
        })
        return context


cancel_moderation_request = ModerationRequestView.as_view(
    action=constants.ACTION_CANCELLED,
    page_title=_('Cancel request'),
    form_class=UpdateModerationRequestForm,
    success_message=_('The moderation request has been cancelled.'),
)

reject_moderation_request = ModerationRequestView.as_view(
    action=constants.ACTION_REJECTED,
    page_title=_('Send for rework'),
    form_class=UpdateModerationRequestForm,
    success_message=_('The moderation request has been sent for rework.'),
)

approve_moderation_request = ModerationRequestView.as_view(
    action=constants.ACTION_APPROVED,
    page_title=_('Approve changes'),
    form_class=UpdateModerationRequestForm,
    success_message=_('The changes have been approved.'),
)

resubmit_moderation_request = ModerationRequestView.as_view(
    action=constants.ACTION_RESUBMITTED,
    page_title=_('Resubmit changes'),
    form_class=UpdateModerationRequestForm,
    success_message=_('The request has been re-submitted.'),
)


class ModerationCommentsView(ListView):

    template_name = 'djangocms_moderation/comment_list.html'

    def dispatch(self, request, page_id, language, *args, **kwargs):
        page_obj = get_page_or_404(page_id, language)
        self.active_request = get_active_moderation_request(page_obj, language)

        if not self.active_request.user_can_view_comments(request.user):
            return HttpResponseForbidden('User is not allowed to view comments.')

        return super(ModerationCommentsView, self).dispatch(
            request, page_id, language, *args, **kwargs
        )

    def get_queryset(self):
        return self.active_request.actions.all()

    def get_context_data(self, **kwargs):
        context = super(ModerationCommentsView, self).get_context_data(**kwargs)
        context.update({
            'title': _('View Comments'),
            'is_popup': True,
        })
        return context


moderation_comments = ModerationCommentsView.as_view()


def moderation_confirmation_page(request, confirmation_id):
    confirmation_page_instance = get_object_or_404(ConfirmationPage, pk=confirmation_id)
    content_view = bool(request.GET.get('content_view'))
    page_id = request.GET.get('page')
    language = request.GET.get('language')

    # Get the correct base template depending on content/build view
    if content_view:
        base_template = 'djangocms_moderation/base_confirmation.html'
    else:
        base_template = 'djangocms_moderation/base_confirmation_build.html'

    context = {
        'opts': ConfirmationPage._meta,
        'app_label': ConfirmationPage._meta.app_label,
        'change': True,
        'add': False,
        'is_popup': True,
        'save_as': False,
        'has_delete_permission': False,
        'has_add_permission': False,
        'has_change_permission': True,
        'instance': confirmation_page_instance,
        'is_form_type': confirmation_page_instance.content_type == constants.CONTENT_TYPE_FORM,
        'content_view': content_view,
        'CONFIRMATION_BASE_TEMPLATE': base_template,
    }

    if request.method == 'POST' and page_id and language:
        context['submitted'] = True
        context['redirect_url'] = add_url_parameters(
            get_admin_url(
                name='cms_moderation_approve_request',
                language=language,
                args=(page_id, language),
            ),
            reviewed=True,
        )
    return render(request, confirmation_page_instance.template, context)


class SubmitCollectionForModeration(FormView):
    template_name = 'djangocms_moderation/request_form.html'
    form_class = SubmitCollectionForModerationForm

    def get_form_kwargs(self):
        kwargs = super(SubmitCollectionForModeration, self).get_form_kwargs()
        kwargs['collection'] = ModerationCollection.objects.get(pk=self.kwargs['collection_id'])
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        try:
            form.save()
        except CollectionCantBeSubmittedForModeration:
            messages.error(self.request, _("This collection can't be submitted for a review"))
        else:
            messages.success(self.request, _("Your collection has been submitted for a review"))
        # Redirect back to the collection filtered moderation request change list
        redirect_url = reverse('admin:djangocms_moderation_moderationrequest_changelist')
        redirect_url = "{}?collection__id__exact={}".format(
            redirect_url,
            form.collection.id
        )
        return HttpResponseRedirect(redirect_url)

    def get_context_data(self, **kwargs):
        context = super(SubmitCollectionForModeration, self).get_context_data(**kwargs)
        context.update({
            'opts': ModerationCollection._meta,
            'title': _('Submit collection for review'),
            'adminform': context['form'],
        })
        return context


submit_collection_for_moderation = SubmitCollectionForModeration.as_view()
