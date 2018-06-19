from __future__ import unicode_literals

from django.conf import settings
from django.contrib import messages
from django.core.urlresolvers import reverse
from django.http import (
    HttpResponseBadRequest,
    HttpResponseForbidden,
    HttpResponseRedirect,
)
from django.shortcuts import render
from django.utils.translation import ugettext_lazy as _
from django.views.generic import FormView, ListView

from cms.models import Page
from cms.utils.urlutils import add_url_parameters

from . import constants
from .forms import (
    ModerationRequestForm,
    SelectModerationForm,
    UpdateModerationRequestForm,
)
from .helpers import (
    get_active_moderation_request,
    get_page_moderation_workflow,
    get_page_or_404,
    get_workflow_or_none,
)
from .models import PageModerationRequest
from .utils import get_admin_url


class ModerationRequestView(FormView):

    action = None
    page_title = None
    success_message = None
    template_name = 'djangocms_moderation/request_form.html'
    success_template_name = 'djangocms_moderation/request_finalized.html'

    def dispatch(self, request, *args, **kwargs):
        user = request.user
        self.language = args[1]
        self.page = get_page_or_404(args[0], self.language)
        self.workflow = None
        self.active_request = get_active_moderation_request(self.page, self.language)

        if self.active_request:
            self.workflow = self.active_request.workflow

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
        elif request.GET.get('workflow'):
            self.workflow = get_workflow_or_none(request.GET.get('workflow'))
        else:
            self.workflow = get_page_moderation_workflow(self.page)

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
        opts = PageModerationRequest._meta
        context = super(ModerationRequestView, self).get_context_data(**kwargs)
        context.update({
            'title': self.page_title,
            'has_change_permission': True,
            'opts': opts,
            'root_path': reverse('admin:index'),
            'app_label': opts.app_label,
            'adminform': context['form'],
            'is_popup': True,
        })
        return context


new_moderation_request = ModerationRequestView.as_view(
    action=constants.ACTION_STARTED,
    page_title=_('Submit for moderation'),
    form_class=ModerationRequestForm,
    success_message=_('The page has been sent for moderation.'),
)

cancel_moderation_request = ModerationRequestView.as_view(
    action=constants.ACTION_CANCELLED,
    page_title=_('Cancel request'),
    form_class=UpdateModerationRequestForm,
    success_message=_('The moderation request has been cancelled.'),
)

reject_moderation_request = ModerationRequestView.as_view(
    action=constants.ACTION_REJECTED,
    page_title=_('Reject changes'),
    form_class=UpdateModerationRequestForm,
    success_message=_('The moderation request has been rejected.'),
)

approve_moderation_request = ModerationRequestView.as_view(
    action=constants.ACTION_APPROVED,
    page_title=_('Approve changes'),
    form_class=UpdateModerationRequestForm,
    success_message=_('The changes have been approved.'),
)


class SelectModerationView(FormView):

    form_class = SelectModerationForm
    template_name = 'djangocms_moderation/select_workflow_form.html'

    def dispatch(self, request, *args, **kwargs):
        self.page_id = args[0]
        self.current_lang = args[1]
        return super(SelectModerationView, self).dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(SelectModerationView, self).get_context_data(**kwargs)
        context.update({
            'has_change_permission': True,
            'root_path': reverse('admin:index'),
            'adminform': context['form'],
            'is_popup': True,
        })
        return context

    def get_form_kwargs(self):
        kwargs = super(SelectModerationView, self).get_form_kwargs()
        kwargs['page'] = get_page_or_404(self.page_id, self.current_lang)
        return kwargs

    def form_valid(self, form):
        selected_workflow = form.cleaned_data['workflow']
        redirect_url = add_url_parameters(
            get_admin_url(
                name='cms_moderation_new_request',
                language=self.current_lang,
                args=(self.page_id, self.current_lang),
            ),
            workflow=selected_workflow.pk
        )
        return HttpResponseRedirect(redirect_url)


select_new_moderation_request = SelectModerationView.as_view()


class ModerationCommentsView(ListView):

    template_name = 'djangocms_moderation/comment_list.html'

    def dispatch(self, request, page_id, language, *args, **kwargs):
        page_obj = get_page_or_404(page_id, language)
        self.active_request = get_active_moderation_request(page_obj, language)
        return super(ModerationCommentsView, self).dispatch(request, page_id, language, *args, **kwargs)

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
