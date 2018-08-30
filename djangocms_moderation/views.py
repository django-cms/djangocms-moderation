from __future__ import unicode_literals

from django.contrib import admin, messages
from django.contrib.contenttypes.models import ContentType
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.utils.translation import ugettext_lazy as _
from django.views.generic import FormView

from cms.models import Page
from cms.utils.urlutils import add_url_parameters

from .forms import CollectionItemForm, SubmitCollectionForModerationForm
from .models import ConfirmationPage, ModerationCollection
from .utils import get_admin_url


from . import constants  # isort:skip


class CollectionItemView(FormView):
    template_name = 'djangocms_moderation/item_to_collection.html'
    form_class = CollectionItemForm
    success_template_name = 'djangocms_moderation/request_finalized.html'

    def get_form_kwargs(self):
        kwargs = super(CollectionItemView, self).get_form_kwargs()
        # TODO: replace page object with Version object
        kwargs['initial'].update({
            'content_object_id': self.request.GET.get('content_object_id'),
            'content_type': ContentType.objects.get_for_model(Page).pk,
        })
        collection_id = self.request.GET.get('collection_id')

        if collection_id:
            kwargs['initial']['collection'] = collection_id
        return kwargs

    def form_valid(self, form):
        content_object = form.cleaned_data['content_object']
        collection = form.cleaned_data['collection']
        collection.add_object(content_object)
        messages.success(self.request, _('Item successfully added to moderation collection'))
        return render(self.request, self.success_template_name, {})

    def get_form(self, **kwargs):
        form = super(CollectionItemView, self).get_form(**kwargs)
        form.set_collection_widget(self.request)
        return form

    def get_context_data(self, **kwargs):
        """
        Gets collection_id from params or from the first collection in the list
        when no ?collection_id is not supplied

        Always gets content_object_list from a collection at a time
        """
        context = super(CollectionItemView, self).get_context_data(**kwargs)
        opts_meta = ModerationCollection._meta
        collection_id = self.request.GET.get('collection_id')

        if collection_id:
            collection = ModerationCollection.objects.get(pk=collection_id)
            content_object_list = collection.moderation_requests.all()
        else:
            content_object_list = []

        model_admin = admin.site._registry[ModerationCollection]
        context.update({
            'content_object_list':  content_object_list,
            'opts': opts_meta,
            'title': _('Add to collection'),
            'form': self.get_form(),
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
        return super(SubmitCollectionForModeration, self).dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super(SubmitCollectionForModeration, self).get_form_kwargs()
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
        context = super(SubmitCollectionForModeration, self).get_context_data(**kwargs)
        context.update({
            'opts': ModerationCollection._meta,
            'title': _('Submit collection for review'),
            'adminform': context['form'],
        })
        return context


submit_collection_for_moderation = SubmitCollectionForModeration.as_view()

