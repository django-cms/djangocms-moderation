from __future__ import unicode_literals

from django.contrib import messages
from django.core.urlresolvers import reverse
from django.http import HttpResponseForbidden, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, render
from django.utils.translation import ugettext_lazy as _
from django.views.generic import FormView

from cms.models import Page

from . import constants
from .forms import ModerationRequestForm, UpdateModerationRequestForm
from .helpers import get_page_moderation_workflow
from .models import PageModerationRequest


class ModerationRequestView(FormView):

    action = None
    page_title = None
    success_message = None
    template_name = 'djangocms_moderation/request_form.html'
    success_template_name = 'djangocms_moderation/request_finalized.html'

    def dispatch(self, request, *args, **kwargs):
        user = request.user
        self.language = args[1]
        self.page = get_object_or_404(
            Page,
            pk=args[0],
            publisher_is_draft=True,
            title_set__language=self.language,
        )
        self.workflow = get_page_moderation_workflow(self.page)

        if not self.workflow:
            # All endpoints require a moderation workflow for the requested page.
            return HttpResponseBadRequest('No moderation workflow exists for page.')

        self.active_request = self.workflow.get_active_request(self.page, self.language)

        if self.active_request:
            needs_ongoing = self.action in (constants.ACTION_APPROVED, constants.ACTION_REJECTED)

            if self.action == constants.ACTION_STARTED:
                # Can't start new request if there's one already.
                return HttpResponseBadRequest('Page already has an active moderation request.')
            elif self.active_request.is_approved and needs_ongoing:
                # Can't reject or approve a moderation request whose steps have all
                # already been approved.
                return HttpResponseBadRequest('Moderation request has already been approved.')
            elif needs_ongoing and not self.active_request.user_can_take_action(user):
                # User can't approve or reject a request where he's not part of the workflow
                return HttpResponseForbidden('User is not allowed to update request.')
        elif self.action != constants.ACTION_STARTED:
            # All except for the new request endpoint require an active moderation request
            return HttpResponseBadRequest('Page does not have an active moderation request.')
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
        opts = PageModerationRequest._meta
        context = super(ModerationRequestView, self).get_context_data(**kwargs)
        context.update({
            'title': self.page_title,
            'has_change_permission': True,
            'opts': opts,
            'root_path': reverse('admin:index'),
            'app_label': opts.app_label,
            'adminform': kwargs['form'],
            'is_popup': True,
        })
        return context


new_moderation_request = ModerationRequestView.as_view(
    action=constants.ACTION_STARTED,
    page_title=_('Submit for moderation'),
    form_class=ModerationRequestForm,
    success_message=_('The page has been sent for moderation.'),
)

reject_moderation_request = ModerationRequestView.as_view(
    action=constants.ACTION_REJECTED,
    page_title=_('Reject changes'),
    form_class=UpdateModerationRequestForm,
    success_message=_('The moderation request has been rejected.'),
)

cancel_moderation_request = ModerationRequestView.as_view(
    action=constants.ACTION_CANCELLED,
    page_title=_('Cancel request'),
    form_class=UpdateModerationRequestForm,
    success_message=_('The moderation request has been cancelled.'),
)

approve_moderation_request = ModerationRequestView.as_view(
    action=constants.ACTION_APPROVED,
    page_title=_('Approve changes'),
    form_class=UpdateModerationRequestForm,
    success_message=_('The changes have been approved.'),
)
