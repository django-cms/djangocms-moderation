from __future__ import unicode_literals

from django import forms
from django.contrib import admin
from django.contrib.admin.widgets import RelatedFieldWidgetWrapper
from django.contrib.auth import get_user_model
from django.forms.forms import NON_FIELD_ERRORS
from django.utils.translation import ugettext, ugettext_lazy as _

from adminsortable2.admin import CustomInlineFormSet
from djangocms_versioning.models import Version

from .constants import (
    ACTION_CANCELLED,
    ACTION_REJECTED,
    ACTION_RESUBMITTED,
    COLLECTING,
)
from .helpers import (
    get_active_moderation_request,
    is_obj_version_unlocked,
    is_registered_for_moderation,
)
from .models import (
    CollectionComment,
    ModerationCollection,
    ModerationRequest,
    ModerationRequestAction,
    RequestComment,
)


class WorkflowStepInlineFormSet(CustomInlineFormSet):

    def validate_unique(self):
        super().validate_unique()
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
        super().__init__(*args, **kwargs)
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
    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

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

    def clean_version(self):
        """
        Make sure that version is not part of another active moderation request
        or version locked to another user
        """
        version = self.cleaned_data['version']

        if not is_registered_for_moderation(version.content):
            raise forms.ValidationError(_(
                "{} is not registered for moderation, please see configuration docs for how to"
                .format(version.content.__class__.__name__)
            ))

        active_moderation_request = get_active_moderation_request(version.content)
        if active_moderation_request:
            raise forms.ValidationError(_(
                "{} is already part of existing moderation request which is part "
                "of another active collection".format(version.content)
            ))

        if not is_obj_version_unlocked(version.content, self.user):
            raise forms.ValidationError(_(
                "{} is version locked to another user".format(version.content)
            ))

        return version


class CollectionItemsForm(forms.Form):
    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

    collection = forms.ModelChoiceField(
        queryset=ModerationCollection.objects.filter(status=COLLECTING),
        required=True
    )
    versions = forms.ModelMultipleChoiceField(
        queryset=Version.objects.all(),
        required=True,
        widget=forms.MultipleHiddenInput(),
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

    def clean_versions(self):
        """
        Process objects which are not part of an active moderation request.
        Other objects are ignored.
        """
        versions = self.cleaned_data['versions']

        versions_eligible_for_moderation_collection = []
        for version in versions:
            active_moderation_request = get_active_moderation_request(version.content)
            if not active_moderation_request and is_obj_version_unlocked(version.content, self.user):
                versions_eligible_for_moderation_collection.append(version.pk)

        if len(versions_eligible_for_moderation_collection) == 0:
            raise forms.ValidationError(_(
                "All items are locked or are already part of an existing moderation request which is part "
                "of another active collection"
            ))
        return Version.objects.filter(pk__in=versions_eligible_for_moderation_collection)


class SubmitCollectionForModerationForm(forms.Form):
    moderator = forms.ModelChoiceField(
        label=_('Select review group'),
        queryset=get_user_model().objects.none(),
        required=False,
    )

    def __init__(self, *args, **kwargs):
        self.collection = kwargs.pop('collection')
        self.user = kwargs.pop('user')
        super().__init__(*args, **kwargs)
        self.configure_moderator_field()

    def configure_moderator_field(self):
        next_role = self.collection.workflow.first_step.role
        users = next_role.get_users_queryset().exclude(pk=self.user.pk)
        self.fields['moderator'].empty_label = ugettext('Any {role}').format(role=next_role.name)
        self.fields['moderator'].queryset = users

    def clean(self):
        if not self.collection.allow_submit_for_review(user=self.user):
            self.add_error(None, _("This collection can't be submitted for a review"))
        return super().clean()

    def save(self):
        self.collection.submit_for_review(
            by_user=self.user,
            to_user=self.cleaned_data.get('moderator'),
        )


class CancelCollectionForm(forms.Form):
    def __init__(self, *args, **kwargs):
        self.collection = kwargs.pop('collection')
        self.user = kwargs.pop('user')
        super().__init__(*args, **kwargs)

    def clean(self):
        if not self.collection.is_cancellable(self.user):
            self.add_error(None, _("This collection can't be cancelled"))
        return super().clean()

    def save(self):
        self.collection.cancel(self.user)


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


class ModerationRequestActionInlineForm(forms.ModelForm):

    class Meta:
        model = ModerationRequestAction
        fields = ('message',)

    def clean_message(self):
        if self.instance and self.cleaned_data['message'] != self.instance.message:
            if self.current_user != self.instance.by_user:
                raise forms.ValidationError(_('You can only change your own comments'))

        return self.cleaned_data['message']
