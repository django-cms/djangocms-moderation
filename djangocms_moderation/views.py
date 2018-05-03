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
from django.views.generic import FormView

from cms.models import Page
from cms.page_rendering import render_page
from cms.utils.urlutils import add_url_parameters

from aldryn_forms.forms import FormSubmissionBaseForm
from aldryn_forms.models import FormSubmission
from djangocms_moderation.contrib.moderation_forms.models import ModerationForm

from . import constants
from .forms import (
    ModerationRequestForm,
    SelectModerationForm,
    UpdateModerationRequestForm,
)
from .helpers import (
    get_action_form_for_step,
    get_action_forms_for_request,
    get_active_moderation_request,
    get_form_submission_or_none,
    get_page_moderation_workflow,
    get_page_or_404,
    get_workflow_or_none,
)
from .models import PageModerationRequest, PageModerationRequestActionFormSubmission
from .utils import get_action_form_submission_url, get_admin_url


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
            elif self.active_request.is_approved and needs_ongoing:
                # Can't reject or approve a moderation request whose steps have all
                # already been approved.
                return HttpResponseBadRequest('Moderation request has already been approved.')
            elif needs_ongoing and not self.active_request.user_can_take_action(user):
                # User can't approve or reject a request where he's not part of the workflow
                return HttpResponseForbidden('User is not allowed to update request.')
            
            next_step = self.active_request.user_get_step(self.request.user)
            approval_form = next_step.role.approval_form if next_step and next_step.role else None

            if approval_form:
                submitted_action_form = get_action_form_for_step(self.active_request, user=user)
                reject_status = (constants.ACTION_REJECTED, constants.ACTION_CANCELLED)

                if self.action == constants.ACTION_APPROVED and not submitted_action_form:
                    # There is an approval form attached and there is no existing submission for that form
                    # Redirect to the attached approval form
                    redirect_url = get_admin_url(
                        name='cms_moderation_submit_action_form',
                        language=self.language,
                        args=(self.page_id, self.language),
                    )
                    return HttpResponseRedirect(redirect_url)
                elif self.action in reject_status and submitted_action_form:
                    # Should not allow to reject/cancel when an approval form is already submitted
                    action_form_url = get_action_form_submission_url(submitted_action_form.action_form.pk)
                    return HttpResponseBadRequest(
                        'Approved action form has already been submitted. \
                        Delete the form submission to reject/cancel the current moderation request. \
                        <a href="{}" target="__blank">{}</a>'.format(
                            action_form_url,
                            submitted_action_form.action_form.name
                        )
                    )
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
        action_form_opts = FormSubmission._meta
        action_forms = list()

        if self.active_request:
            for instance in get_action_forms_for_request(self.active_request):
                action_forms.append({
                    'step': instance.for_step,
                    'action_form': instance.action_form,
                })

        context = super(ModerationRequestView, self).get_context_data(**kwargs)
        context.update({
            'title': self.page_title,
            'has_change_permission': True,
            'opts': opts,
            'root_path': reverse('admin:index'),
            'app_label': opts.app_label,
            'adminform': context['form'],
            'is_popup': True,
            'action_forms': action_forms,
            'action_form_opts': action_form_opts,
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


class ModerationActionFormSubmitView(FormView):

    template_name = 'djangocms_moderation/moderation_action_form.html'
    form_class = FormSubmissionBaseForm

    def dispatch(self, request, *args, **kwargs):
        self.request = request
        self.page_id = args[0]
        self.current_lang = args[1]
        self.page = get_page_or_404(self.page_id, self.current_lang)
        self.active_request = get_active_moderation_request(self.page, self.current_lang)
        next_step = self.active_request.user_get_step(self.request.user)
        role = next_step.role

        if not role or not role.approval_form:
            return HttpResponseBadRequest('There is no form attached with this role.')

        # Get the first form plugin instance in the page
        self.form_plugin = ModerationForm.objects.filter(placeholder__page=role.approval_form).first()

        if not self.form_plugin:
            return HttpResponseBadRequest('There is not form built in the attached form page.')

        if request.method == 'POST' and self.form_plugin:
            form_plugin_instance = self.form_plugin.get_plugin_instance()[1]
            form = form_plugin_instance.process_form(self.form_plugin, request)

            if form.is_valid():
                return self.form_valid(form)
        return super(ModerationActionFormSubmitView, self).dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super(ModerationActionFormSubmitView, self).get_context_data(**kwargs)
        form_plugin_class_instance = self.form_plugin.get_plugin_class_instance()
        form_context = form_plugin_class_instance.render({'request': self.request}, self.form_plugin, None)
        context.update({
            'has_change_permission': True,
            'root_path': reverse('admin:index'),
            'adminform': form_context['form'],
            'is_popup': True,
        })
        return context

    def get_form_kwargs(self):
        kwargs = super(ModerationActionFormSubmitView, self).get_form_kwargs()
        kwargs['request'] = self.request
        kwargs['form_plugin'] = self.form_plugin
        return kwargs

    def form_valid(self, plugin_form):
        # Save action form submission
        action_form_submission = PageModerationRequestActionFormSubmission(
            request=self.active_request,
            for_step=self.active_request.user_get_step(self.request.user),
            action_form=plugin_form.instance,
            by_user=self.request.user,
        )
        action_form_submission.save()

        redirect_url = get_admin_url(
            name='cms_moderation_approve_request',
            language=self.current_lang,
            args=(self.page_id, self.current_lang),
        )
        return HttpResponseRedirect(redirect_url)


moderation_action_form_submit_view = ModerationActionFormSubmitView.as_view()
