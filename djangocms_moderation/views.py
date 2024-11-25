from urllib.parse import quote

from django.contrib import admin, messages
from django.db import transaction
from django.http import Http404, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils.translation import gettext_lazy as _, ngettext
from django.views.generic import FormView

from cms.models import PageContent
from cms.utils.urlutils import add_url_parameters

from djangocms_versioning.models import Version

from .forms import (
    CancelCollectionForm,
    CollectionItemsForm,
    SubmitCollectionForModerationForm,
)
from .models import ConfirmationPage, ModerationCollection
from .utils import get_admin_url


from . import constants  # isort:skip


@method_decorator(transaction.atomic, name="post")
class CollectionItemsView(FormView):
    template_name = "djangocms_moderation/items_to_collection.html"
    form_class = CollectionItemsForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def get_initial(self):
        initial = super().get_initial()
        ids = self.request.GET.get("version_ids", "").split(",")
        ids = [int(x) for x in ids if x.isdigit()]
        versions = Version.objects.filter(pk__in=ids)
        initial["versions"] = versions

        collection_id = self.request.GET.get("collection_id")
        if collection_id:
            initial["collection"] = collection_id
        return initial

    def form_valid(self, form):
        versions = form.cleaned_data["versions"]
        collection = form.cleaned_data["collection"]

        total_added = 0
        for version in versions:
            include_children = (
                isinstance(version.content, PageContent)
                and version.created_by == self.request.user
            )
            moderation_request, added_items = collection.add_version(
                version, include_children=include_children
            )
            total_added += added_items

        messages.success(
            self.request,
            ngettext(
                "%(count)d item successfully added to moderation collection",
                "%(count)d items successfully added to moderation collection",
                total_added,
            )
            % {"count": total_added},
        )

        return self._get_success_redirect()

    def _get_success_redirect(self):
        """
        Lets work out where should we redirect the user after they've added
        versions to a collection
        """
        return_to_url = self.request.GET.get("return_to_url")
        if return_to_url:
            url_is_safe = url_has_allowed_host_and_scheme(
                url=return_to_url,
                allowed_hosts=self.request.get_host(),
                require_https=self.request.is_secure(),
            )
            # Protect against refracted XSS attacks
            # Allow : in http://, ?=& for GET parameters
            return_to_url = quote(return_to_url, safe='/:?=&')
            if not url_is_safe:
                return_to_url = self.request.path
            return HttpResponseRedirect(return_to_url)

        success_template = "djangocms_moderation/request_finalized.html"
        return render(self.request, success_template, {})

    def get_form(self, **kwargs):
        form = super().get_form(**kwargs)
        form.set_collection_widget(self.request)
        return form

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        opts_meta = ModerationCollection._meta

        collection_id = self.request.GET.get("collection_id")
        if collection_id:
            try:
                collection = ModerationCollection.objects.get(pk=int(collection_id))
            except (ValueError, ModerationCollection.DoesNotExist, TypeError):
                raise Http404
            else:
                moderation_requests = collection.moderation_requests.all()
        else:
            moderation_requests = []

        model_admin = admin.site._registry[ModerationCollection]
        context.update(
            {
                "moderation_requests": moderation_requests,
                "opts": opts_meta,
                "form": self.get_form(),
                "collection_id": collection_id,
                "media": model_admin.media,
            }
        )
        return context


add_items_to_collection = CollectionItemsView.as_view()


def moderation_confirmation_page(request, confirmation_id):
    """
    This is an implementation of Aldryn-forms to provide a review confirmation page
    """
    confirmation_page_instance = get_object_or_404(ConfirmationPage, pk=confirmation_id)
    content_view = bool(request.GET.get("content_view"))
    page_id = request.GET.get("page")
    language = request.GET.get("language")

    # Get the correct base template depending on content/build view
    if content_view:
        base_template = "djangocms_moderation/base_confirmation.html"
    else:
        base_template = "djangocms_moderation/base_confirmation_build.html"

    context = {
        "opts": ConfirmationPage._meta,
        "app_label": ConfirmationPage._meta.app_label,
        "change": True,
        "add": False,
        "is_popup": True,
        "save_as": False,
        "has_delete_permission": False,
        "has_add_permission": False,
        "has_change_permission": True,
        "instance": confirmation_page_instance,
        "is_form_type": confirmation_page_instance.content_type
        == constants.CONTENT_TYPE_FORM,
        "content_view": content_view,
        "CONFIRMATION_BASE_TEMPLATE": base_template,
    }

    if request.method == "POST" and page_id and language:
        context["submitted"] = True
        context["redirect_url"] = add_url_parameters(
            get_admin_url(
                name="cms_moderation_approve_request",
                language=language,
                args=(page_id, language),
            ),
            reviewed=True,
        )
    return render(request, confirmation_page_instance.template, context)


class SubmitCollectionForModeration(FormView):
    template_name = "djangocms_moderation/request_form.html"
    form_class = SubmitCollectionForModerationForm
    collection = None  # Populated in dispatch method

    def dispatch(self, request, *args, **kwargs):
        self.collection = get_object_or_404(
            ModerationCollection, pk=self.kwargs["collection_id"]
        )
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["collection"] = self.collection
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.save()
        messages.success(
            self.request, _("Your collection has been submitted for review")
        )
        # Redirect back to the collection filtered moderation request change list
        redirect_url = reverse('admin:djangocms_moderation_moderationrequest_changelist')
        redirect_url = "{}?moderation_request__collection__id={}".format(
            redirect_url,
            self.collection.id
        )
        return HttpResponseRedirect(redirect_url)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "opts": ModerationCollection._meta,
                "title": _("Submit collection for review"),
                "adminform": context["form"],
            }
        )
        return context


submit_collection_for_moderation = SubmitCollectionForModeration.as_view()


class CancelCollection(FormView):
    template_name = "djangocms_moderation/cancel_collection.html"
    form_class = CancelCollectionForm
    collection = None  # Populated in dispatch method

    def dispatch(self, request, *args, **kwargs):
        self.collection = get_object_or_404(
            ModerationCollection, pk=self.kwargs["collection_id"]
        )
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["collection"] = self.collection
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        form.save()
        messages.success(self.request, _("Your collection has been cancelled"))
        # Redirect back to the collection filtered moderation request change list
        redirect_url = reverse(
            "admin:djangocms_moderation_moderationcollection_changelist"
        )
        return HttpResponseRedirect(redirect_url)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({"collection": self.collection, "title": _("Cancel collection")})
        return context


cancel_collection = CancelCollection.as_view()
