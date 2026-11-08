from datetime import date
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from ..models import MaintenanceEntry
from ..services import build_maintenance_reminders, format_license_plate


@pytest.mark.parametrize(
    ("license_plate", "formatted"),
    [
        ("YG64PV", "YG-64-PV"),
        ("yg-64-pv", "YG-64-PV"),
        ("12ABC3", "12-ABC-3"),
        ("9ABC12", "9-ABC-12"),
    ],
)
def test_license_plate_is_formatted(license_plate, formatted):
    assert format_license_plate(license_plate) == formatted


@pytest.mark.django_db
def test_maintenance_reminders_use_latest_category_interval(user, vehicle):
    entries = []
    for performed_on, odometer in ((date(2025, 1, 1), 240000), (date(2025, 7, 1), 245000)):
        entries.append(
            MaintenanceEntry.objects.create(
                vehicle=vehicle,
                created_by=user,
                performed_on=performed_on,
                odometer_km=odometer,
                category="oil",
                description="Olie vervangen",
                performed_by="self",
            )
        )

    reminders = build_maintenance_reminders(entries, current_odometer=250000, today=date(2025, 8, 1))

    assert reminders[0]["category"] == "Oliebeurt"
    assert reminders[0]["due_date"] == date(2025, 12, 29)
    assert reminders[0]["due_odometer"] == 250000
    assert reminders[0]["status"] == "due"


@pytest.mark.django_db
def test_vehicle_detail_shows_maintenance_reminders(client, user, vehicle):
    client.force_login(user)
    for performed_on, odometer in ((date(2025, 1, 1), 240000), (date(2025, 7, 1), 245000)):
        MaintenanceEntry.objects.create(
            vehicle=vehicle,
            created_by=user,
            performed_on=performed_on,
            odometer_km=odometer,
            category="oil",
            description="Olie vervangen",
            performed_by="self",
        )

    response = client.get(reverse("maintenance:vehicle-detail", args=[vehicle.pk]))

    assert response.status_code == 200
    assert "Verwachte herinneringen" in response.content.decode()


@pytest.mark.django_db
def test_rdw_lookup_returns_vehicle_data(client, user):
    client.force_login(user)
    payload = [
        {
            "merk": "VOLVO",
            "handelsbenaming": "240",
            "datum eerste toelating": "19900101",
            "brandstof_omschrijving": "Benzine",
        }
    ]

    with patch("maintenance.services.requests.get") as get:
        get.return_value.json.return_value = payload
        get.return_value.raise_for_status.return_value = None
        response = client.get(reverse("maintenance:rdw-lookup"), {"license_plate": "ab-12-cd"})

    assert response.status_code == 200
    assert response.json()["make"] == "Volvo"
    assert response.json()["year"] == 1990
    get.assert_called_once()


@pytest.mark.django_db
def test_invoice_analysis_prefills_maintenance_fields(client, user, vehicle):
    client.force_login(user)
    line_item = SimpleNamespace(
        type_="line_item",
        mention_text="",
        properties=[
            SimpleNamespace(type_="line_item/description", mention_text="Remblokken vervangen"),
            SimpleNamespace(type_="line_item/description", mention_text="Remschijven controleren"),
        ],
    )
    entities = [
        SimpleNamespace(type_="invoice_date", mention_text="01-03-2026"),
        SimpleNamespace(type_="total_amount", mention_text="€ 125,00"),
        SimpleNamespace(type_="invoice_id", mention_text="123"),
        SimpleNamespace(type_="supplier_name", mention_text="Garage Noord"),
        line_item,
    ]
    document = SimpleNamespace(entities=entities, text="Kilometerstand: 251.000 km Remblokken vervangen")
    document_response = SimpleNamespace(document=document)
    upload = SimpleUploadedFile("factuur.jpg", b"image", content_type="image/jpeg")

    with patch.dict(
        "os.environ",
        {
            "GOOGLE_CLOUD_PROJECT": "test",
            "GOOGLE_DOCUMENT_AI_LOCATION": "eu",
            "GOOGLE_DOCUMENT_AI_PROCESSOR_ID": "test",
        },
    ), patch(
        "maintenance.services.invoice.documentai_v1.DocumentProcessorServiceClient"
    ) as document_client:
        document_client.return_value.processor_path.return_value = "projects/test/locations/eu/processors/test"
        document_client.return_value.get_processor.return_value.name = (
            "projects/test/locations/eu/processors/test"
        )
        document_client.return_value.process_document.return_value = document_response
        response = client.post(
            reverse("maintenance:invoice-analyze", args=[vehicle.pk]),
            {"invoice_file": upload},
        )

    assert response.status_code == 200
    assert response.json()["description"] == "Remblokken vervangen; Remschijven controleren"
    assert response.json()["category"] == "brakes"
    assert response.json()["total_cost"] == "125.00"


@pytest.mark.django_db
def test_invoice_analysis_does_not_use_personal_details_as_description(client, user, vehicle):
    client.force_login(user)
    document = SimpleNamespace(
        entities=[
            SimpleNamespace(type_="supplier_name", mention_text="Garage Noord"),
        ],
        text="Jan Jansen\nDorpsstraat 12\n1234 AB Amsterdam\nOnderhoudsfactuur",
    )
    document_response = SimpleNamespace(document=document)
    upload = SimpleUploadedFile("factuur.jpg", b"image", content_type="image/jpeg")

    with patch.dict(
        "os.environ",
        {
            "GOOGLE_CLOUD_PROJECT": "test",
            "GOOGLE_DOCUMENT_AI_LOCATION": "eu",
            "GOOGLE_DOCUMENT_AI_PROCESSOR_ID": "test",
        },
    ), patch(
        "maintenance.services.invoice.documentai_v1.DocumentProcessorServiceClient"
    ) as document_client:
        document_client.return_value.processor_path.return_value = "projects/test/locations/eu/processors/test"
        document_client.return_value.get_processor.return_value.name = (
            "projects/test/locations/eu/processors/test"
        )
        document_client.return_value.process_document.return_value = document_response
        response = client.post(
            reverse("maintenance:invoice-analyze", args=[vehicle.pk]),
            {"invoice_file": upload},
        )

    assert response.status_code == 200
    assert response.json()["description"] == "Onderhoud volgens factuur"
    assert "Jan Jansen" not in response.json()["description"]
    assert "Dorpsstraat" not in response.json()["description"]


@pytest.mark.django_db
def test_invoice_analysis_uses_parts_total_and_ignores_shipping(client, user, vehicle):
    client.force_login(user)
    def line_item(description, price):
        return SimpleNamespace(
            type_="line_item",
            mention_text="",
            properties=[
                SimpleNamespace(type_="line_item/description", mention_text=description),
                SimpleNamespace(type_="line_item/quantity", mention_text="2"),
                SimpleNamespace(type_="line_item/unit_price", mention_text=price),
            ],
        )

    document = SimpleNamespace(
        entities=[
            line_item("Remblok", "50,00"),
            line_item("Verzendkosten", "15,00"),
            SimpleNamespace(type_="total_amount", mention_text="115,00"),
        ],
        text="Totaal: 115,00",
    )
    upload = SimpleUploadedFile("factuur.jpg", b"image", content_type="image/jpeg")

    with patch.dict(
        "os.environ",
        {
            "GOOGLE_CLOUD_PROJECT": "test",
            "GOOGLE_DOCUMENT_AI_LOCATION": "eu",
            "GOOGLE_DOCUMENT_AI_PROCESSOR_ID": "test",
        },
    ), patch(
        "maintenance.services.invoice.documentai_v1.DocumentProcessorServiceClient"
    ) as document_client:
        document_client.return_value.processor_path.return_value = "projects/test/locations/eu/processors/test"
        document_client.return_value.get_processor.return_value.name = (
            "projects/test/locations/eu/processors/test"
        )
        document_client.return_value.process_document.return_value.document = document
        response = client.post(
            reverse("maintenance:invoice-analyze", args=[vehicle.pk]),
            {"invoice_file": upload},
        )

    assert response.status_code == 200
    assert response.json()["total_cost"] == "100.00"
    assert len(response.json()["parts"]) == 1
