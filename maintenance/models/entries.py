import hashlib
from decimal import ROUND_HALF_UP, Decimal

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q

from .choices import MaintenanceCategory, TrustLevel, Visibility
from .vehicles import Vehicle

MONEY_QUANTUM = Decimal("0.01")


def round_money(value):
    return Decimal(value).quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP)


class MaintenanceEntry(models.Model):
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, related_name="maintenance_entries")
    performed_on = models.DateField()
    odometer_km = models.PositiveIntegerField()
    category = models.CharField(max_length=20, choices=MaintenanceCategory.choices)
    description = models.TextField()
    performed_by = models.CharField(max_length=20, choices=[("self", "Zelf"), ("garage", "Garage")])
    total_cost = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal("0.00"), validators=[MinValueValidator(Decimal("0"))]
    )
    currency = models.CharField(max_length=3, default="EUR")
    notes = models.TextField(blank=True)
    trust_level = models.CharField(max_length=20, choices=TrustLevel.choices, default=TrustLevel.SELF_REPORTED)
    visibility = models.CharField(max_length=10, choices=Visibility.choices, default=Visibility.PRIVATE)
    version = models.PositiveIntegerField(default=1)
    supersedes = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, blank=True, related_name="superseding_entries"
    )
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-performed_on", "-odometer_km"]
        constraints = [
            models.CheckConstraint(condition=Q(total_cost__gte=0), name="maintenance_cost_nonnegative"),
        ]

    def clean(self):
        if self.supersedes and self.supersedes.vehicle_id != self.vehicle_id:
            raise ValidationError({"supersedes": "Een versie moet bij hetzelfde voertuig horen."})

    def save(self, *args, **kwargs):
        self.total_cost = round_money(self.total_cost)
        super().save(*args, **kwargs)


class PartUsed(models.Model):
    entry = models.ForeignKey(MaintenanceEntry, on_delete=models.CASCADE, related_name="parts")
    description = models.CharField(max_length=255, blank=True)
    brand = models.CharField(max_length=100, blank=True)
    part_number = models.CharField(max_length=100, blank=True)
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal("0"))])

    class Meta:
        constraints = [
            models.CheckConstraint(condition=Q(quantity__gt=0), name="part_quantity_positive"),
            models.CheckConstraint(condition=Q(unit_price__gte=0), name="part_price_nonnegative"),
        ]

    def save(self, *args, **kwargs):
        self.unit_price = round_money(self.unit_price)
        super().save(*args, **kwargs)


class Attachment(models.Model):
    entry = models.ForeignKey(MaintenanceEntry, on_delete=models.CASCADE, related_name="attachments")
    file = models.FileField(upload_to="maintenance/%Y/%m/")
    content_type = models.CharField(max_length=100)
    sha256 = models.CharField(max_length=64, editable=False)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.sha256 and self.file:
            self.file.seek(0)
            self.sha256 = hashlib.sha256(self.file.read()).hexdigest()
            self.file.seek(0)
        super().save(*args, **kwargs)


class Verification(models.Model):
    entry = models.ForeignKey(MaintenanceEntry, on_delete=models.CASCADE, related_name="verifications")
    checked_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.PROTECT)
    method = models.CharField(max_length=20, choices=[("backoffice", "Backoffice"), ("ai", "AI")])
    outcome = models.CharField(
        max_length=20,
        choices=[("approved", "Goedgekeurd"), ("rejected", "Afgewezen"), ("needs_review", "Nader onderzoek")],
    )
    explanation = models.TextField()
    model_name = models.CharField(max_length=100, blank=True)
    model_version = models.CharField(max_length=100, blank=True)
    checked_at = models.DateTimeField(auto_now_add=True)
