import json

from django.db import transaction
from django.db.models import Sum
from django.urls import reverse_lazy
from django.utils import timezone
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from ..forms import AttachmentForm, VehicleForm
from ..models import Ownership, Transfer, Vehicle
from ..services import build_maintenance_reminders
from .base import OwnerVehicleMixin


class VehicleListView(OwnerVehicleMixin, ListView):
    template_name = "maintenance/vehicle_list.html"
    context_object_name = "vehicles"


class VehicleCreateView(OwnerVehicleMixin, CreateView):
    model = Vehicle
    form_class = VehicleForm
    template_name = "maintenance/vehicle_form.html"
    success_url = reverse_lazy("maintenance:vehicle-list")

    def form_valid(self, form):
        form.instance.owner = self.request.user
        response = super().form_valid(form)
        Ownership.objects.create(user=self.request.user, vehicle=self.object, from_date=timezone.localdate())
        return response


class VehicleUpdateView(OwnerVehicleMixin, UpdateView):
    model = Vehicle
    form_class = VehicleForm
    template_name = "maintenance/vehicle_form.html"
    success_url = reverse_lazy("maintenance:vehicle-list")


class VehicleDeleteView(OwnerVehicleMixin, DeleteView):
    model = Vehicle
    template_name = "maintenance/vehicle_confirm_delete.html"
    success_url = reverse_lazy("maintenance:vehicle-list")

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        with transaction.atomic():
            Transfer.objects.filter(vehicle_id=self.object.pk).delete()
            self.object.audit_logs.all().delete()
            return super().delete(request, *args, **kwargs)


class VehicleDetailView(OwnerVehicleMixin, DetailView):
    template_name = "maintenance/vehicle_detail.html"
    context_object_name = "vehicle"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        entries = self.object.maintenance_entries.all()
        context.update(
            entries=entries,
            maintenance_reminders=build_maintenance_reminders(
                entries,
                current_odometer=self.object.current_odometer_km,
            ),
            total_cost=entries.aggregate(total=Sum("total_cost"))["total"] or 0,
            attachment_form=AttachmentForm(),
            chart_data=json.dumps(
                {
                    "labels": [str(entry.performed_on) for entry in entries],
                    "costs": [float(entry.total_cost) for entry in entries],
                    "odometers": [entry.odometer_km for entry in entries],
                }
            ),
        )
        return context
