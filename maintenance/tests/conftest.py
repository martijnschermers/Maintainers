from datetime import date

import pytest
from django.contrib.auth import get_user_model

from ..models import MaintenanceEntry, Vehicle


@pytest.fixture
def user(db):
    return get_user_model().objects.create_user(username="martijn", password="Strong-test-password-123!")


@pytest.fixture
def vehicle(user):
    return Vehicle.objects.create(owner=user, make="Volvo", model="240", current_odometer_km=250000)


@pytest.fixture
def entry(user, vehicle):
    return MaintenanceEntry.objects.create(
        vehicle=vehicle,
        created_by=user,
        performed_on=date(2026, 1, 1),
        odometer_km=250000,
        category="oil",
        description="Olie vervangen",
        performed_by="self",
    )
