from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.views.generic import CreateView, DeleteView, View

from ..forms import AttachmentForm, MaintenanceEntryForm, PartUsedFormSet
from ..models import Attachment, MaintenanceEntry, Vehicle
from ..services import analyze_invoice


class MaintenanceEntryCreateView(LoginRequiredMixin, CreateView):
    model = MaintenanceEntry
    form_class = MaintenanceEntryForm
    template_name = "maintenance/entry_form.html"

    def dispatch(self, request, *args, **kwargs):
        self.vehicle = get_object_or_404(Vehicle, pk=kwargs["vehicle_id"], owner=request.user)
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        part_formset = PartUsedFormSet(self.request.POST, instance=form.instance, prefix="parts")
        if not part_formset.is_valid():
            return self.form_invalid(form)
        parts_total = sum(
            item["quantity"] * item["unit_price"]
            for item in part_formset.cleaned_data
            if item and item.get("description") and not item.get("DELETE")
        )
        with transaction.atomic():
            form.instance.vehicle = self.vehicle
            form.instance.created_by = self.request.user
            if parts_total:
                form.instance.total_cost = parts_total
            response = super().form_valid(form)
            part_formset.instance = self.object
            part_formset.save()
        invoice_file = form.cleaned_data.get("invoice_file")
        if invoice_file:
            Attachment.objects.create(
                entry=self.object,
                file=invoice_file,
                content_type=invoice_file.content_type,
                uploaded_by=self.request.user,
            )
        return response

    def get_success_url(self):
        return reverse("maintenance:vehicle-detail", args=[self.vehicle.pk])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["vehicle"] = self.vehicle
        context["part_formset"] = kwargs.get("part_formset") or PartUsedFormSet(
            instance=self.object, prefix="parts"
        )
        return context

    def form_invalid(self, form):
        context = self.get_context_data(
            form=form, part_formset=PartUsedFormSet(self.request.POST, prefix="parts")
        )
        return self.render_to_response(context)


class MaintenanceEntryUpdateView(MaintenanceEntryCreateView):
    def dispatch(self, request, *args, **kwargs):
        self.entry = get_object_or_404(
            MaintenanceEntry.objects.select_related("vehicle").prefetch_related("parts"),
            pk=kwargs["pk"],
            vehicle__owner=request.user,
        )
        self.vehicle = self.entry.vehicle
        return LoginRequiredMixin.dispatch(self, request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["instance"] = self.entry
        return kwargs

    def form_valid(self, form):
        part_formset = PartUsedFormSet(self.request.POST, instance=self.entry, prefix="parts")
        if not part_formset.is_valid():
            return self.form_invalid(form)
        parts_total = sum(
            item["quantity"] * item["unit_price"]
            for item in part_formset.cleaned_data
            if item and item.get("description") and not item.get("DELETE")
        )
        with transaction.atomic():
            form.instance.vehicle = self.vehicle
            if parts_total:
                form.instance.total_cost = parts_total
            response = super(MaintenanceEntryCreateView, self).form_valid(form)
            part_formset.instance = self.object
            part_formset.save()
        invoice_file = form.cleaned_data.get("invoice_file")
        if invoice_file:
            Attachment.objects.create(
                entry=self.object,
                file=invoice_file,
                content_type=invoice_file.content_type,
                uploaded_by=self.request.user,
            )
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["vehicle"] = self.vehicle
        context["entry"] = self.entry
        context["part_formset"] = kwargs.get("part_formset") or PartUsedFormSet(
            instance=self.entry, prefix="parts"
        )
        return context


class MaintenanceEntryDeleteView(LoginRequiredMixin, DeleteView):
    model = MaintenanceEntry
    template_name = "maintenance/entry_confirm_delete.html"

    def get_queryset(self):
        return MaintenanceEntry.objects.filter(vehicle__owner=self.request.user).select_related("vehicle")

    def get_success_url(self):
        return reverse("maintenance:vehicle-detail", args=[self.object.vehicle_id])


class InvoiceAnalysisView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        get_object_or_404(Vehicle, pk=kwargs["vehicle_id"], owner=request.user)
        uploaded_file = request.FILES.get("invoice_file")
        if uploaded_file is None:
            return JsonResponse({"error": "Selecteer eerst een factuur."}, status=400)
        try:
            return JsonResponse(analyze_invoice(uploaded_file))
        except (ValidationError, KeyError) as error:
            return JsonResponse({"error": str(error)}, status=502)


class AttachmentCreateView(LoginRequiredMixin, CreateView):
    model = Attachment
    form_class = AttachmentForm
    template_name = "maintenance/attachment_form.html"

    def dispatch(self, request, *args, **kwargs):
        self.entry = get_object_or_404(
            MaintenanceEntry.objects.select_related("vehicle"), pk=kwargs["entry_id"], vehicle__owner=request.user
        )
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.entry = self.entry
        form.instance.uploaded_by = self.request.user
        form.instance.content_type = form.cleaned_data["file"].content_type
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("maintenance:vehicle-detail", args=[self.entry.vehicle_id])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(entry=self.entry, vehicle=self.entry.vehicle)
        return context
