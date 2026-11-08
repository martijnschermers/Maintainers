from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone
from django.utils.html import format_html
from django.views.generic import DetailView, TemplateView, View

from ..models import Ownership, ShareLink, Transfer, Vehicle


class TransferCreateView(LoginRequiredMixin, TemplateView):
    template_name = "maintenance/transfer_form.html"

    def post(self, request, *args, **kwargs):
        vehicle = get_object_or_404(Vehicle, pk=kwargs["pk"], owner=request.user)
        transfer = Transfer.objects.create(
            vehicle=vehicle,
            from_user=request.user,
            expires_at=timezone.now() + timedelta(days=14),
        )
        link = request.build_absolute_uri(f"/transfer/{transfer.token}/")
        messages.success(
            request,
            format_html(
                'Overdrachtslink aangemaakt: <a class="text-mint underline" href="{0}">{0}</a>',
                link,
            ),
        )
        return redirect("maintenance:vehicle-detail", pk=vehicle.pk)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["vehicle"] = get_object_or_404(Vehicle, pk=self.kwargs["pk"], owner=self.request.user)
        return context


class ShareLinkCreateView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        vehicle = get_object_or_404(Vehicle, pk=kwargs["pk"], owner=request.user)
        share_link, _ = ShareLink.objects.get_or_create(
            vehicle=vehicle,
            defaults={"created_by": request.user},
        )
        if not share_link.active:
            share_link.active = True
            share_link.created_by = request.user
            share_link.save(update_fields=["active", "created_by"])
        link = request.build_absolute_uri(reverse("maintenance:share-public", args=[share_link.token]))
        messages.success(
            request,
            format_html(
                'Deellink aangemaakt: <a class="text-mint underline" href="{0}">{0}</a>',
                link,
            ),
        )
        return redirect("maintenance:vehicle-detail", pk=vehicle.pk)


class PublicShareLinkView(DetailView):
    model = ShareLink
    template_name = "maintenance/share_public.html"
    context_object_name = "share_link"

    def get_object(self, queryset=None):
        return get_object_or_404(
            ShareLink.objects.select_related("vehicle"),
            token=self.kwargs["token"],
            active=True,
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["entries"] = self.object.vehicle.maintenance_entries.filter(visibility="public")
        return context


class PublicTransferView(DetailView):
    model = Transfer
    template_name = "maintenance/transfer_public.html"
    context_object_name = "transfer"

    def get_object(self, queryset=None):
        transfer = get_object_or_404(
            Transfer.objects.select_related("vehicle"), token=self.kwargs["token"], status=Transfer.Status.OPEN
        )
        if transfer.expires_at <= timezone.now():
            raise Http404
        return transfer

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["entries"] = self.object.vehicle.maintenance_entries.filter(visibility="public")
        return context


class TransferAcceptView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        with transaction.atomic():
            transfer = get_object_or_404(
                Transfer.objects.select_for_update(), token=kwargs["token"], status=Transfer.Status.OPEN
            )
            if transfer.expires_at <= timezone.now():
                raise Http404
            vehicle = transfer.vehicle
            vehicle.owner = request.user
            vehicle.save(update_fields=["owner", "updated_at"])
            transfer.to_user = request.user
            transfer.status = Transfer.Status.ACCEPTED
            transfer.accepted_at = timezone.now()
            transfer.save(update_fields=["to_user", "status", "accepted_at"])
            Ownership.objects.filter(vehicle=vehicle, until_date__isnull=True).update(until_date=timezone.localdate())
            Ownership.objects.create(user=request.user, vehicle=vehicle, from_date=timezone.localdate())
        return redirect("maintenance:vehicle-list")
