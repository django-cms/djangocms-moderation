from __future__ import unicode_literals

from django import forms
from django.contrib import admin
from django.contrib.admin.widgets import RelatedFieldWidgetWrapper
from django.contrib.auth import get_user_model
from django.forms.forms import NON_FIELD_ERRORS
from django.utils.translation import ugettext, ugettext_lazy as _

from adminsortable2.admin import CustomInlineFormSet
from djangocms_versioning.models import Version

from djangocms_moderation.utils import get_active_moderation_request
from .constants import (
    ACTION_CANCELLED,
    ACTION_REJECTED,
    ACTION_RESUBMITTED,
    COLLECTING,
)
from .models import (
    CollectionComment,
    ModerationCollection,
    ModerationRequest,
    RequestComment,
)


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


class UpdateModerationRequestForm(forms.Form):
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
        super(UpdateModerationRequestForm, self).__init__(*args, **kwargs)
        self.configure_moderator_field()

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
            current_step = self.active_request.user_get_step(self.user)
            next_step = current_step.get_next() if current_step else None

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


class CollectionItemForm(forms.Form):

    collection = forms.ModelChoiceField(
        queryset=ModerationCollection.objects.filter(status=COLLECTING),
        required=True
    )
    version = forms.ModelChoiceField(
        queryset=Version.objects.all(),
        required=True,
        widget=forms.HiddenInput(),
    )

    def set_collection_widget(self, request):
        related_modeladmin = admin.site._registry.get(ModerationCollection)
        dbfield = ModerationRequest._meta.get_field('collection')
        formfield = self.fields['collection']
        formfield.widget = RelatedFieldWidgetWrapper(
            formfield.widget,
            dbfield.rel,
            admin_site=admin.site,
            can_add_related=related_modeladmin.has_add_permission(request),
            can_change_related=related_modeladmin.has_change_permission(request),
            can_delete_related=related_modeladmin.has_delete_permission(request),
        )

    def clean(self):
        """
        Validates content_object_id: Checks that a given content_object_id has
        a content_object and it is not currently part of any ModerationRequest

        :return:
        """
        if self.errors:
            return self.cleaned_data

        version = self.cleaned_data['version']

        active_moderation_request = get_active_moderation_request(version.content)
        if active_moderation_request:
            raise forms.ValidationError(_(
                "{} is already part of existing moderation request which is part "
                "of another active collection".format(version.content)
            ))

        self.cleaned_data['version'] = version
        return self.cleaned_data


class SubmitCollectionForModerationForm(forms.Form):
    moderator = forms.ModelChoiceField(
        label=_('Select review group'),
        queryset=get_user_model().objects.none(),
        required=False,
    )

    def __init__(self, *args, **kwargs):
        self.collection = kwargs.pop('collection')
        self.user = kwargs.pop('user')
        super(SubmitCollectionForModerationForm, self).__init__(*args, **kwargs)
        self.configure_moderator_field()

    def configure_moderator_field(self):
        next_role = self.collection.workflow.first_step.role
        users = next_role.get_users_queryset().exclude(pk=self.user.pk)
        self.fields['moderator'].empty_label = ugettext('Any {role}').format(role=next_role.name)
        self.fields['moderator'].queryset = users

    def clean(self):
        if not self.collection.allow_submit_for_review(user=self.user):
            self.add_error(None, _("This collection can't be submitted for a review"))
        return super(SubmitCollectionForModerationForm, self).clean()

    def save(self):
        self.collection.submit_for_review(
            by_user=self.user,
            to_user=self.cleaned_data.get('moderator'),
        )


class CollectionCommentForm(forms.ModelForm):
    """
    The author and moderation request should be pre-filled and non-editable.
    NB: Hidden fields seems to be the only reliable way to do this;
    readonly fields do not work for add, only for edit.
    """
    class Meta:
        model = CollectionComment
        fields = '__all__'
        widgets = {
            'author': forms.HiddenInput(),
            'collection': forms.HiddenInput(),
        }


class RequestCommentForm(forms.ModelForm):
    """
    The author and moderation request should be pre-filled and non-editable.
    NB: Hidden fields seems to be the only reliable way to do this;
    readonly fields do not work for add, only for edit.
    """
    class Meta:
        model = RequestComment
        fields = '__all__'
        widgets = {
            'author': forms.HiddenInput(),
            'moderation_request': forms.HiddenInput(),
        }
