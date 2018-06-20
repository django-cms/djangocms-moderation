from __future__ import unicode_literals

from django import forms
from django.forms.forms import NON_FIELD_ERRORS
from django.contrib.auth import get_user_model
from django.utils.translation import ugettext, ugettext_lazy as _

from adminsortable2.admin import CustomInlineFormSet

from .constants import ACTION_CANCELLED, ACTION_REJECTED, ACTION_RESUBMITTED
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

    def configure_moderator_field(self):
        next_role = self.workflow.first_step.role
        users = next_role.get_users_queryset().exclude(pk=self.user.pk)
        self.fields['moderator'].empty_label = ugettext('Any {role}').format(role=next_role.name)
        self.fields['moderator'].queryset = users

    def save(self):
        self.workflow.submit_new_request(
            page=self.page,
            by_user=self.user,
            to_user=self.cleaned_data.get('moderator'),
            language=self.language,
            message=self.cleaned_data['message'],
        )


class UpdateModerationRequestForm(ModerationRequestForm):

    def configure_moderator_field(self):
        # For cancelling and rejecting, we don't need to display a moderator
        # field.
        if self.action in (ACTION_CANCELLED, ACTION_REJECTED):
            self.fields['moderator'].queryset = get_user_model().objects.none()
            self.fields['moderator'].widget = forms.HiddenInput()
            return

        # If the content author is resubmitting the work after a rejected
        # moderation request, the next step will be the first one - as it has
        # to be approved again from the beginning
        if self.action == ACTION_RESUBMITTED:
            next_step = self.active_request.workflow.first_step
        else:
            try:
                next_step = self.active_request.user_get_step(self.user).get_next()
            except AttributeError:
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
            to_user=self.cleaned_data.get('moderator'),
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
