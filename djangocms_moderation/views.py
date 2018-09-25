from __future__ import unicode_literals

from django.contrib import admin, messages
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect, Http404
from django.shortcuts import get_object_or_404, render
from django.utils.translation import ugettext_lazy as _
from django.views.generic import FormView

from cms.utils.urlutils import add_url_parameters

from djangocms_versioning.admin import GROUPER_PARAM
from djangocms_versioning.models import Version

from .forms import (
    CancelCollectionForm,
    CollectionItemForm,
    SubmitCollectionForModerationForm,
)
from .models import ConfirmationPage, ModerationCollection
from .utils import get_admin_url


from . import constants  # isort:skip


class CollectionItemView(FormView):
    template_name = 'djangocms_moderation/item_to_collection.html'
    form_class = CollectionItemForm
    success_template_name = 'djangocms_moderation/request_finalized.html'

    def get_form_kwargs(self):
        kwargs = super(CollectionItemView, self).get_form_kwargs()
        kwargs['initial'].update({
            'version': self.request.GET.get('version_id'),
        })
        collection_id = self.request.GET.get('collection_id')

        if collection_id:
            kwargs['initial']['collection'] = collection_id
        return kwargs

    def form_valid(self, form):
        version = form.cleaned_data['version']
        collection = form.cleaned_data['collection']
        collection.add_version(version)
        messages.success(self.request, _('Item successfully added to moderation collection'))

        # Return different response if we opened the view as a modal
        if self.request.GET.get('_modal'):
            return render(self.request, self.success_template_name, {})
        else:
            # Otherwise redirect to the grouper changelist as this is likely
            # the place this view was called from
            changelist_url = reverse(
                'admin:{app}_{model}version_changelist'.format(
                    app=version._meta.app_label,
                    model=version.content._meta.model_name,
                )
            )
            url = "{changelist_url}?{grouper_param}={grouper_id}".format(
                changelist_url=changelist_url,
                grouper_param=GROUPER_PARAM,
                grouper_id=version.grouper.id,
            )
            return HttpResponseRedirect(url)

    def get_form(self, **kwargs):
        form = super().get_form(**kwargs)
        form.set_collection_widget(self.request)
        return form

    def get_context_data(self, **kwargs):
        """
        Gets collection_id from params or from the first collection in the list
        when no ?collection_id is not supplied

        Always gets content_object_list from a collection at a time
        """
        context = super().get_context_data(**kwargs)
        opts_meta = ModerationCollection._meta
        collection_id = self.request.GET.get('collection_id')
        version_id = self.request.GET.get('version_id')

        if collection_id:
            try:
                collection = ModerationCollection.objects.get(pk=int(collection_id))
            except (ValueError, ModerationCollection.DoesNotExist):
                raise Http404
            else:
                moderation_request_list = collection.moderation_requests.all()
        else:
            moderation_request_list = []

        if version_id:
            try:
                version = Version.objects.get(pk=int(version_id))
            except (ValueError, Version.DoesNotExist):
                raise Http404
        else:
            version = None

        model_admin = admin.site._registry[ModerationCollection]
        context.update({
            'moderation_request_list': moderation_request_list,
            'opts': opts_meta,
            'title': _('Add to collection'),
            'form': self.get_form(),
            'version': version,
            'media': model_admin.media,
        })

        return context


add_item_to_collection = CollectionItemView.as_view()


def moderation_confirmation_page(request, confirmation_id):
    """
    This is an implementation of Aldryn-forms to provide a review confirmation page
    """
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
    collection = None  # Populated in dispatch method

    def dispatch(self, request, *args, **kwargs):
        self.collection = get_object_or_404(
            ModerationCollection,
            pk=self.kwargs['collection_id'],
        )
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['collection'] = self.collection
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.save()
        messages.success(self.request, _("Your collection has been submitted for review"))
        # Redirect back to the collection filtered moderation request change list
        redirect_url = reverse('admin:djangocms_moderation_moderationrequest_changelist')
        redirect_url = "{}?collection__id__exact={}".format(
            redirect_url,
            self.collection.id
        )
        return HttpResponseRedirect(redirect_url)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'opts': ModerationCollection._meta,
            'title': _('Submit collection for review'),
            'adminform': context['form'],
        })
        return context


submit_collection_for_moderation = SubmitCollectionForModeration.as_view()


class CancelCollection(FormView):
    template_name = 'djangocms_moderation/cancel_collection.html'
    form_class = CancelCollectionForm
    collection = None  # Populated in dispatch method

    def dispatch(self, request, *args, **kwargs):
        self.collection = get_object_or_404(
            ModerationCollection,
            pk=self.kwargs['collection_id'],
        )
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['collection'] = self.collection
        kwargs['user'] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.save()
        messages.success(self.request, _("Your collection has been cancelled"))
        # Redirect back to the collection filtered moderation request change list
        redirect_url = reverse('admin:djangocms_moderation_moderationcollection_changelist')
        return HttpResponseRedirect(redirect_url)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        collection_id = self.request.GET.get('collection_id')

        collection = None
        try:
            if collection_id:
                collection = ModerationCollection.objects.get(pk=int(collection_id))
        except (ValueError, ModerationCollection.DoesNotExist):
            raise Http404

        context.update({
            'collection': collection,
            'title': _('Cancel collection'),
        })

        return context


cancel_collection = CancelCollection.as_view()
