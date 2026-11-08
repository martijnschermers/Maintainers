import requests
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404
from django.views.generic import View
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from ..models import Vehicle
from ..services import export_user_data, export_vehicle_csv, lookup_rdw_license_plate


class RdwLookupView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        try:
            return JsonResponse(lookup_rdw_license_plate(request.GET.get("license_plate", "")))
        except (ValidationError, ValueError) as error:
            return JsonResponse({"error": str(error)}, status=400)
        except requests.RequestException as error:
            return JsonResponse({"error": str(error)}, status=502)


class VehicleCsvExportView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        vehicle = get_object_or_404(Vehicle, pk=kwargs["pk"], owner=request.user)
        response = HttpResponse(export_vehicle_csv(vehicle), content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = f'attachment; filename="{vehicle.make}-{vehicle.model}-onderhoud.csv"'
        return response


class VehiclePdfExportView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        vehicle = get_object_or_404(Vehicle, pk=kwargs["pk"], owner=request.user)
        response = HttpResponse(content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="{vehicle.make}-{vehicle.model}-dossier.pdf"'
        pdf = canvas.Canvas(response, pagesize=A4)
        width, height = A4
        y = height - 60
        pdf.setFont("Helvetica-Bold", 20)
        pdf.drawString(50, y, f"{vehicle.make} {vehicle.model}")
        y -= 35
        pdf.setFont("Helvetica", 10)
        pdf.drawString(50, y, f"Kenteken: {vehicle.license_plate} | Kilometerstand: {vehicle.current_odometer_km} km")
        y -= 30
        for entry in vehicle.maintenance_entries.all():
            if y < 70:
                pdf.showPage()
                y = height - 60
            pdf.drawString(
                50,
                y,
                (
                    f"{entry.performed_on} | {entry.odometer_km} km | "
                    f"{entry.description[:60]} | {entry.total_cost:.2f} EUR"
                ),
            )
            y -= 16
        pdf.save()
        return response


class UserDataExportView(LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        response = JsonResponse(export_user_data(request.user), json_dumps_params={"indent": 2})
        response["Content-Disposition"] = 'attachment; filename="maintainers-data-export.json"'
        return response
