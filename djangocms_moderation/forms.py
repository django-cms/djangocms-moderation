from django import forms
from django.contrib.auth import get_user_model
from django.utils.translation import ugettext, ugettext_lazy as _

from .constants import ACTION_CANCELLED, ACTION_REJECTED


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
