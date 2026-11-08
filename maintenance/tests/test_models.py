from datetime import date
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

from ..models import MaintenanceCategory, MaintenanceEntry, PartUsed


@pytest.mark.django_db
def test_vehicle_is_owned_by_user(user, vehicle):
    assert list(user.vehicles.all()) == [vehicle]


@pytest.mark.django_db
def test_maintenance_cost_must_not_be_negative(user, vehicle):
    entry = MaintenanceEntry(
        vehicle=vehicle,
        created_by=user,
        performed_on=date(2026, 1, 1),
        odometer_km=250000,
        category=MaintenanceCategory.OIL,
        description="Olie vervangen",
        performed_by="self",
        total_cost=Decimal("-1.00"),
    )
    with pytest.raises(ValidationError):
        entry.full_clean()


@pytest.mark.django_db
def test_prices_are_rounded_to_two_decimals_on_save(user, vehicle):
    entry = MaintenanceEntry.objects.create(
        vehicle=vehicle,
        created_by=user,
        performed_on=date(2026, 1, 1),
        odometer_km=250000,
        category=MaintenanceCategory.OIL,
        description="Olie vervangen",
        performed_by="self",
        total_cost=Decimal("12.345"),
    )
    part = PartUsed.objects.create(entry=entry, description="Filter", unit_price=Decimal("4.567"))

    entry.refresh_from_db()
    part.refresh_from_db()
    assert entry.total_cost == Decimal("12.35")
    assert part.unit_price == Decimal("4.57")


@pytest.mark.django_db
def test_maintenance_entries_can_be_updated(user, vehicle):
    entry = MaintenanceEntry.objects.create(
        vehicle=vehicle,
        created_by=user,
        performed_on=date(2026, 1, 1),
        odometer_km=250000,
        category=MaintenanceCategory.OIL,
        description="Olie vervangen",
        performed_by="self",
    )
    entry.description = "Aangepast"
    entry.save()
    entry.refresh_from_db()
    assert entry.description == "Aangepast"


@pytest.mark.django_db
def test_different_user_cannot_become_vehicle_owner_without_ownership_record(user, vehicle):
    other_user = get_user_model().objects.create_user(
        username="other", password="Strong-test-password-123!"
    )
    assert vehicle not in other_user.vehicles.all()
