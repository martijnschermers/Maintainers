from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone
from django.views.generic import DetailView, TemplateView, View

from ..models import Ownership, Transfer, Vehicle


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
        messages.success(request, f"Overdrachtslink aangemaakt: {link}")
        return redirect("maintenance:vehicle-detail", pk=vehicle.pk)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["vehicle"] = get_object_or_404(Vehicle, pk=self.kwargs["pk"], owner=self.request.user)
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
