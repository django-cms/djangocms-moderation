from __future__ import unicode_literals

from django import forms
from django.forms.forms import NON_FIELD_ERRORS
from django.contrib.auth import get_user_model
from django.utils.translation import ugettext, ugettext_lazy as _

from adminsortable2.admin import CustomInlineFormSet

from .constants import ACTION_CANCELLED, ACTION_REJECTED
from .helpers import get_page_moderation_workflow
from .models import Workflow


class WorkflowStepInlineFormSet(CustomInlineFormSet):

    def validate_unique(self):
        super(WorkflowStepInlineFormSet, self).validate_unique()
        # The following fixes a bug in Django where it doesn't validate unique constraint
        # when the parent model in inline relationship has not been saved
        errors = []
        unique_check = ('role', 'workflow')
        selected_roles = []
        forms_to_delete = self.deleted_forms
        valid_forms = [form for form in self.forms if form.is_valid() and form not in forms_to_delete]

        for form in valid_forms:
            selected_role = form.cleaned_data.get('role')

            if not selected_role:
                continue

            if selected_role.pk in selected_roles:
                # poke error messages into the right places and mark
                # the form as invalid
                errors.append(self.get_unique_error_message(unique_check))
                form._errors[NON_FIELD_ERRORS] = self.error_class([self.get_form_error()])
                # remove the data from the cleaned_data dict since it was invalid
                for field in unique_check:
                    if field in form.cleaned_data:
                        del form.cleaned_data[field]
            else:
                selected_roles.append(selected_role.pk)


class ModerationRequestForm(forms.Form):
    moderator = forms.ModelChoiceField(
        label=_('moderator'),
        queryset=get_user_model().objects.none(),
        required=False,
    )
    message = forms.CharField(
        label=_('comment'),
        required=False,
        widget=forms.Textarea(),
    )

    def __init__(self, *args, **kwargs):
        self.action = kwargs.pop('action')
        self.language = kwargs.pop('language')
        self.page = kwargs.pop('page')
        self.user = kwargs.pop('user')
        self.workflow = kwargs.pop('workflow')
        self.active_request = kwargs.pop('active_request')
        super(ModerationRequestForm, self).__init__(*args, **kwargs)

        if 'moderator' in self.fields:
            self.configure_moderator_field()

    def get_moderator(self):
        return self.cleaned_data.get('moderator')

    def configure_moderator_field(self):
        next_role = self.workflow.first_step.role
        users = next_role.get_users_queryset().exclude(pk=self.user.pk)
        self.fields['moderator'].empty_label = ugettext('Any {role}').format(role=next_role.name)
        self.fields['moderator'].queryset = users

    def save(self):
        self.workflow.submit_new_request(
            page=self.page,
            by_user=self.user,
            to_user=self.get_moderator(),
            language=self.language,
            message=self.cleaned_data['message'],
        )


class UpdateModerationRequestForm(ModerationRequestForm):

    def configure_moderator_field(self):
        if self.action in (ACTION_CANCELLED, ACTION_REJECTED):
            self.fields['moderator'].queryset = get_user_model().objects.none()
            self.fields['moderator'].widget = forms.HiddenInput()
            return

        user_step = self.active_request.user_get_step(self.user)

        if user_step:
            next_step = user_step.get_next()
        else:
            next_step = None

        if next_step:
            next_role = next_step.role
            users = next_step.role.get_users_queryset()
            self.fields['moderator'].empty_label = ugettext('Any {role}').format(role=next_role.name)
            self.fields['moderator'].queryset = users.exclude(pk=self.user.pk)
        else:
            self.fields['moderator'].queryset = get_user_model().objects.none()
            self.fields['moderator'].widget = forms.HiddenInput()

    def save(self):
        self.active_request.update_status(
            action=self.action,
            by_user=self.user,
            to_user=self.get_moderator(),
            message=self.cleaned_data['message'],
        )


class SelectModerationForm(forms.Form):
    required_css_class = 'required'

    workflow = forms.ModelChoiceField(
        label=_('workflow to trigger'),
        queryset=Workflow.objects.all(),
        required=True,
    )

    def __init__(self, *args, **kwargs):
        page = kwargs.pop('page')
        super(SelectModerationForm, self).__init__(*args, **kwargs)
        self.fields['workflow'].initial = get_page_moderation_workflow(page)
