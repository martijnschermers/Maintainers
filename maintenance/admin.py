from django.contrib import admin

from .models import (
    Attachment,
    AuditLog,
    MaintenanceEntry,
    Ownership,
    PartUsed,
    Transfer,
    Vehicle,
    Verification,
)


@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display = ("make", "model", "license_plate", "owner", "current_odometer_km")
    list_filter = ("vehicle_type", "fuel_type")
    search_fields = ("make", "model", "license_plate", "vin", "owner__username")


@admin.register(MaintenanceEntry)
class MaintenanceEntryAdmin(admin.ModelAdmin):
    list_display = (
        "vehicle",
        "performed_on",
        "category",
        "trust_level",
        "visibility",
        "total_cost",
    )
    list_filter = ("trust_level", "visibility", "category", "performed_by")
    search_fields = ("vehicle__make", "vehicle__model", "description")
    readonly_fields = ("created_at",)


admin.site.register([Attachment, AuditLog, Ownership, PartUsed, Transfer, Verification])
