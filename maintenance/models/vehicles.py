from django.conf import settings
from django.db import models
from django.db.models import Q

from .choices import FuelType, VehicleType


class Vehicle(models.Model):
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="vehicles")
    vehicle_type = models.CharField(max_length=20, choices=VehicleType.choices, default=VehicleType.CAR)
    make = models.CharField("merk", max_length=100)
    model = models.CharField(max_length=100)
    year = models.PositiveSmallIntegerField(null=True, blank=True)
    license_plate = models.CharField(max_length=12, blank=True)
    vin = models.CharField(max_length=17, blank=True)
    fuel_type = models.CharField(max_length=20, choices=FuelType.choices, blank=True)
    current_odometer_km = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["make", "model"]
        constraints = [
            models.CheckConstraint(condition=Q(current_odometer_km__gte=0), name="vehicle_odometer_nonnegative"),
            models.UniqueConstraint(fields=["vin"], condition=~Q(vin=""), name="unique_nonempty_vehicle_vin"),
            models.UniqueConstraint(
                fields=["license_plate"],
                condition=~Q(license_plate=""),
                name="unique_nonempty_vehicle_license_plate",
            ),
        ]

    def __str__(self):
        return f"{self.make} {self.model}"


class Ownership(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="ownerships")
    vehicle = models.ForeignKey("Vehicle", on_delete=models.CASCADE, related_name="ownerships")
    from_date = models.DateField()
    until_date = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ["-from_date"]
        constraints = [
            models.CheckConstraint(
                condition=Q(until_date__isnull=True) | Q(until_date__gte=models.F("from_date")),
                name="ownership_until_after_from",
            ),
            models.UniqueConstraint(
                fields=["vehicle", "user", "from_date"], name="unique_vehicle_user_start_date"
            ),
        ]

    def clean(self):
        from django.core.exceptions import ValidationError

        if self.until_date and self.until_date < self.from_date:
            raise ValidationError({"until_date": "De einddatum mag niet voor de startdatum liggen."})
