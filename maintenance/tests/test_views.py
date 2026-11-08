from datetime import date, timedelta
from decimal import Decimal
from hashlib import sha256

import pytest
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse
from django.utils import timezone

from ..models import Attachment, MaintenanceEntry, Ownership, ShareLink, Transfer, Vehicle


@pytest.mark.django_db
def test_vehicle_list_only_shows_logged_in_users_vehicles(client, user, vehicle):
    other_user = get_user_model().objects.create_user(
        username="other", password="Strong-test-password-123!"
    )
    Vehicle.objects.create(owner=other_user, make="Ford", model="Transit")
    client.force_login(user)

    response = client.get(reverse("maintenance:vehicle-list"))

    assert response.status_code == 200
    assert "Volvo" in response.content.decode()
    assert "Ford" not in response.content.decode()


@pytest.mark.django_db
def test_vehicle_update_cannot_access_another_users_vehicle(client, user, vehicle):
    other_user = get_user_model().objects.create_user(
        username="other", password="Strong-test-password-123!"
    )
    client.force_login(other_user)

    response = client.get(reverse("maintenance:vehicle-update", args=[vehicle.pk]))

    assert response.status_code == 404


@pytest.mark.django_db
def test_vehicle_delete_requires_confirmation_and_deletes_vehicle(client, user, vehicle):
    client.force_login(user)
    confirmation = client.get(reverse("maintenance:vehicle-delete", args=[vehicle.pk]))
    assert confirmation.status_code == 200
    assert "Voertuig definitief verwijderen" in confirmation.content.decode()

    response = client.post(reverse("maintenance:vehicle-delete", args=[vehicle.pk]))

    assert response.status_code == 302
    assert not Vehicle.objects.filter(pk=vehicle.pk).exists()


@pytest.mark.django_db
def test_vehicle_delete_removes_protected_transfers(client, user, vehicle):
    Transfer.objects.create(
        vehicle=vehicle,
        from_user=user,
        expires_at=timezone.now() + timedelta(days=14),
    )
    client.force_login(user)

    response = client.post(reverse("maintenance:vehicle-delete", args=[vehicle.pk]))

    assert response.status_code == 302
    assert not Vehicle.objects.filter(pk=vehicle.pk).exists()
    assert not Transfer.objects.filter(vehicle=vehicle).exists()


@pytest.mark.django_db
def test_maintenance_entry_delete_requires_confirmation_and_deletes_entry(client, user, vehicle, entry):
    client.force_login(user)
    confirmation = client.get(reverse("maintenance:entry-delete", args=[entry.pk]))
    assert confirmation.status_code == 200
    assert "Onderhoud definitief verwijderen" in confirmation.content.decode()

    response = client.post(reverse("maintenance:entry-delete", args=[entry.pk]))

    assert response.status_code == 302
    assert not MaintenanceEntry.objects.filter(pk=entry.pk).exists()


@pytest.mark.django_db
def test_maintenance_entry_delete_keeps_superseding_entry(client, user, vehicle, entry):
    superseding_entry = MaintenanceEntry.objects.create(
        vehicle=vehicle,
        created_by=user,
        performed_on=entry.performed_on,
        odometer_km=entry.odometer_km,
        category=entry.category,
        description="Aangepaste onderhoudsbeurt",
        performed_by=entry.performed_by,
        supersedes=entry,
    )
    client.force_login(user)

    response = client.post(reverse("maintenance:entry-delete", args=[entry.pk]))

    assert response.status_code == 302
    assert not MaintenanceEntry.objects.filter(pk=entry.pk).exists()
    superseding_entry.refresh_from_db()
    assert superseding_entry.supersedes is None


@pytest.mark.django_db
def test_user_can_update_existing_maintenance_entry(client, user, vehicle, entry):
    client.force_login(user)
    response = client.get(reverse("maintenance:entry-update", args=[entry.pk]))

    assert response.status_code == 200
    content = response.content.decode()
    assert "Onderhoud bewerken" in content
    assert "Nieuwe versie opslaan" in content
    assert 'name="performed_on" value="2026-01-01"' in content

    response = client.post(
        reverse("maintenance:entry-update", args=[entry.pk]),
        {
            "performed_on": "2026-02-01",
            "odometer_km": "251000",
            "category": "oil",
            "description": "Olie en filter vervangen",
            "performed_by": "garage",
            "total_cost": "75.00",
            "notes": "Bijgewerkt na factuurcontrole",
            "trust_level": "evidence",
            "visibility": "private",
            "parts-TOTAL_FORMS": "1",
            "parts-INITIAL_FORMS": "0",
            "parts-MIN_NUM_FORMS": "0",
            "parts-MAX_NUM_FORMS": "1000",
            "parts-0-id": "",
            "parts-0-description": "Oliefilter",
            "parts-0-brand": "Bosch",
            "parts-0-part_number": "OF-1",
            "parts-0-quantity": "1",
            "parts-0-unit_price": "12.50",
        },
    )

    assert response.status_code == 302
    updated = MaintenanceEntry.objects.get(pk=entry.pk)
    assert updated.description == "Olie en filter vervangen"
    assert updated.version == entry.version
    assert updated.parts.get().description == "Oliefilter"


@pytest.mark.django_db
def test_user_cannot_update_another_users_maintenance_entry(client, entry):
    other_user = get_user_model().objects.create_user(
        username="other", password="Strong-test-password-123!"
    )
    client.force_login(other_user)

    response = client.get(reverse("maintenance:entry-update", args=[entry.pk]))

    assert response.status_code == 404


@pytest.mark.django_db
def test_user_cannot_delete_another_users_maintenance_entry(client, entry):
    other_user = get_user_model().objects.create_user(
        username="other", password="Strong-test-password-123!"
    )
    client.force_login(other_user)
    response = client.get(reverse("maintenance:entry-delete", args=[entry.pk]))
    assert response.status_code == 404


@pytest.mark.django_db
def test_vehicle_form_dropdowns_use_tailwind_classes(client, user):
    client.force_login(user)
    content = client.get(reverse("maintenance:vehicle-create")).content.decode()
    assert 'name="vehicle_type"' in content
    assert 'name="fuel_type"' in content
    assert "border-slate-700" in content
    assert "focus:border-emerald-300" in content


@pytest.mark.django_db
def test_vehicle_form_labels_are_in_dutch(client, user):
    client.force_login(user)
    content = client.get(reverse("maintenance:vehicle-create")).content.decode()
    assert "Voertuigtype" in content
    assert "Bouwjaar" in content
    assert "Chassisnummer (VIN)" not in content
    assert "Huidige kilometerstand" in content
    assert "Vehicle type" not in content


@pytest.mark.django_db
def test_vehicle_form_starts_with_rdw_lookup(client, user):
    client.force_login(user)
    content = client.get(reverse("maintenance:vehicle-create")).content.decode()
    assert content.index("01 / Kenteken") < content.index("02 / Identificatie")
    assert "Kenteken (optioneel)" in content


@pytest.mark.django_db
def test_user_can_create_project_vehicle_without_license_plate(client, user):
    client.force_login(user)
    response = client.post(
        reverse("maintenance:vehicle-create"),
        {
            "vehicle_type": "car",
            "make": "Kitcar",
            "model": "Project",
            "license_plate": "",
            "current_odometer_km": "0",
        },
    )
    assert response.status_code == 302
    vehicle = Vehicle.objects.get(make="Kitcar", model="Project")
    assert vehicle.license_plate == ""


@pytest.mark.django_db
def test_maintenance_form_labels_are_in_dutch(client, user, vehicle):
    client.force_login(user)
    content = client.get(reverse("maintenance:entry-create", args=[vehicle.pk])).content.decode()
    assert "Datum uitgevoerd" in content
    assert "Kilometerstand" in content
    assert "Uitgevoerd door" in content
    assert "Vertrouwensniveau" in content


@pytest.mark.django_db
def test_invoice_analysis_is_hidden_and_disabled_by_default(client, user, vehicle):
    client.force_login(user)

    form_response = client.get(reverse("maintenance:entry-create", args=[vehicle.pk]))
    analysis_response = client.post(reverse("maintenance:invoice-analyze", args=[vehicle.pk]))

    assert "Factuur analyseren" not in form_response.content.decode()
    assert analysis_response.status_code == 404
    assert analysis_response.json()["error"] == "Factuuranalyse is momenteel niet beschikbaar."


@pytest.mark.django_db
@override_settings(FEATURE_INVOICE_ANALYSIS_ENABLED=True)
def test_invoice_analysis_can_be_enabled(client, user, vehicle):
    client.force_login(user)

    response = client.get(reverse("maintenance:entry-create", args=[vehicle.pk]))

    assert "Factuur analyseren" in response.content.decode()


@pytest.mark.django_db
def test_root_shows_landing_page_for_anonymous_users(client):
    response = client.get(reverse("maintenance:home"))
    assert response.status_code == 200
    content = response.content.decode()
    assert "Een betrouwbaar dossier" in content
    assert 'name="description"' in content
    assert 'application/ld+json' in content


@pytest.mark.django_db
def test_root_shows_dashboard_for_authenticated_users(client, user):
    client.force_login(user)
    response = client.get(reverse("maintenance:home"))
    assert response.status_code == 200
    assert "Goed onderhoud begint hier." in response.content.decode()


@pytest.mark.django_db
def test_dashboard_formats_odometer_with_km_and_thousands_separator(client, user, vehicle):
    client.force_login(user)
    content = client.get(reverse("maintenance:dashboard")).content.decode()
    assert "250.000 km" in content


@pytest.mark.django_db
def test_maintenance_actions_are_prominent_at_top_of_item(client, user, vehicle, entry):
    client.force_login(user)
    content = client.get(reverse("maintenance:vehicle-detail", args=[vehicle.pk])).content.decode()

    actions_position = content.index(">Bewerken</a>")
    description_position = content.index(entry.description)
    assert actions_position < description_position
    assert ">Verwijderen</a>" in content


@pytest.mark.django_db
def test_mobile_navigation_uses_hamburger_menu(client, user):
    client.force_login(user)
    content = client.get(reverse("maintenance:home")).content.decode()
    assert 'id="mobile-menu-button"' in content
    assert 'aria-controls="mobile-menu"' in content
    assert 'id="mobile-menu"' in content
    assert "md:flex" in content


@pytest.mark.django_db
def test_theme_switch_is_available_on_all_pages(client):
    content = client.get(reverse("maintenance:home")).content.decode()
    assert 'class="theme-toggle' in content
    assert "maintainers-theme" in content
    assert 'prefers-color-scheme: light' in content


@pytest.mark.django_db
def test_user_can_add_maintenance_entry(client, user, vehicle):
    client.force_login(user)
    response = client.post(
        reverse("maintenance:entry-create", args=[vehicle.pk]),
        {
            "performed_on": "2026-02-01",
            "odometer_km": "250500",
            "category": "oil",
            "description": "Olie en filter vervangen",
            "performed_by": "self",
            "total_cost": "42.50",
            "currency": "EUR",
            "notes": "",
            "trust_level": "self_reported",
            "visibility": "private",
            "parts-TOTAL_FORMS": "1",
            "parts-INITIAL_FORMS": "0",
            "parts-MIN_NUM_FORMS": "0",
            "parts-MAX_NUM_FORMS": "1000",
            "parts-0-description": "Oliefilter",
            "parts-0-brand": "Bosch",
            "parts-0-part_number": "OF-123",
            "parts-0-quantity": "1",
            "parts-0-unit_price": "12.50",
        },
    )
    assert response.status_code == 302
    maintenance_entry = vehicle.maintenance_entries.get()
    assert maintenance_entry.description == "Olie en filter vervangen"
    assert maintenance_entry.total_cost == Decimal("12.50")
    assert maintenance_entry.parts.get().description == "Oliefilter"


@pytest.mark.django_db
def test_user_can_upload_a_supported_attachment(client, user, entry):
    client.force_login(user)
    content = b"%PDF-1.7 invoice contents"
    upload = SimpleUploadedFile("factuur.pdf", content, content_type="application/pdf")
    response = client.post(reverse("maintenance:attachment-create", args=[entry.pk]), {"file": upload})
    attachment = Attachment.objects.get(entry=entry)
    assert response.status_code == 302
    assert attachment.content_type == "application/pdf"
    assert attachment.sha256 == sha256(content).hexdigest()


@pytest.mark.django_db
def test_attachment_upload_rejects_unsupported_file_type(client, user, entry):
    client.force_login(user)
    upload = SimpleUploadedFile("script.exe", b"not allowed", content_type="application/x-msdownload")
    response = client.post(reverse("maintenance:attachment-create", args=[entry.pk]), {"file": upload})
    assert response.status_code == 200
    assert not Attachment.objects.filter(entry=entry).exists()
    assert "Upload alleen een PDF" in response.content.decode()


@pytest.mark.django_db
def test_user_cannot_upload_attachment_to_another_users_entry(client, entry):
    other_user = get_user_model().objects.create_user(
        username="other", password="Strong-test-password-123!"
    )
    client.force_login(other_user)
    upload = SimpleUploadedFile("factuur.pdf", b"invoice", content_type="application/pdf")
    response = client.post(reverse("maintenance:attachment-create", args=[entry.pk]), {"file": upload})
    assert response.status_code == 404


@pytest.mark.django_db
def test_allauth_login_page_exposes_google_and_apple(client):
    response = client.get(reverse("account_login"))
    content = response.content.decode()
    assert response.status_code == 200
    assert "accounts/google/login/" in content
    assert "accounts/apple/login/" in content
    assert reverse("account_signup") in content
    assert reverse("account_reset_password") in content


@pytest.mark.django_db
def test_password_reset_page_is_styled_and_available(client):
    response = client.get(reverse("account_reset_password"))
    content = response.content.decode()
    assert response.status_code == 200
    assert "Wachtwoord vergeten?" in content
    assert 'name="email"' in content
    assert "Herstellink versturen" in content


@pytest.mark.django_db
def test_password_reset_request_shows_neutral_confirmation(client):
    reset_user = get_user_model().objects.create_user(
        username="reset-user",
        email="reset@example.com",
        password="Strong-test-password-123!",
    )
    response = client.post(reverse("account_reset_password"), {"email": reset_user.email})
    assert response.status_code == 302
    assert response.url == reverse("account_reset_password_done")


@pytest.mark.django_db
def test_allauth_signup_page_uses_the_styled_template(client):
    response = client.get(reverse("account_signup"))
    content = response.content.decode()
    assert response.status_code == 200
    assert "Account maken" in content
    assert "bg-mint" in content
    assert 'name="username"' in content


@pytest.mark.django_db
def test_vehicle_creation_creates_ownership_record(client, user):
    client.force_login(user)
    response = client.post(
        reverse("maintenance:vehicle-create"),
        {"vehicle_type": "car", "make": "Volvo", "model": "240", "current_odometer_km": "250000"},
    )
    vehicle = Vehicle.objects.get(make="Volvo")
    assert response.status_code == 302
    assert Ownership.objects.filter(user=user, vehicle=vehicle, until_date__isnull=True).exists()


@pytest.mark.django_db
def test_vehicle_creation_formats_license_plate(client, user):
    client.force_login(user)
    response = client.post(
        reverse("maintenance:vehicle-create"),
        {
            "vehicle_type": "car",
            "make": "Volvo",
            "model": "240",
            "license_plate": "yg64pv",
            "current_odometer_km": "250000",
        },
    )
    assert response.status_code == 302
    assert Vehicle.objects.get(make="Volvo").license_plate == "YG-64-PV"


@pytest.mark.django_db
def test_vehicle_creation_rejects_duplicate_license_plate(client, user, vehicle):
    client.force_login(user)
    vehicle.license_plate = "YG-64-PV"
    vehicle.save(update_fields=["license_plate"])
    response = client.post(
        reverse("maintenance:vehicle-create"),
        {
            "vehicle_type": "car",
            "make": "Ford",
            "model": "Focus",
            "license_plate": "yg64pv",
            "current_odometer_km": "120000",
        },
    )
    assert response.status_code == 200
    assert "Dit kenteken is al aan een voertuig gekoppeld." in response.content.decode()
    assert not Vehicle.objects.filter(make="Ford").exists()


@pytest.mark.django_db
def test_maintenance_form_uses_styled_euro_fields(client, user, vehicle):
    client.force_login(user)
    response = client.get(reverse("maintenance:entry-create", args=[vehicle.pk]))
    content = response.content.decode()
    assert 'name="currency"' not in content
    assert "file-input" in content
    assert 'name="category"' in content


@pytest.mark.django_db
def test_vehicle_exports_are_available_to_owner(client, user, vehicle, entry):
    client.force_login(user)
    csv_response = client.get(reverse("maintenance:vehicle-export-csv", args=[vehicle.pk]))
    pdf_response = client.get(reverse("maintenance:vehicle-export-pdf", args=[vehicle.pk]))
    assert csv_response.status_code == 200
    assert "Olie vervangen" in csv_response.content.decode()
    assert pdf_response.status_code == 200
    assert pdf_response["Content-Type"] == "application/pdf"
    assert pdf_response.content.startswith(b"%PDF")


@pytest.mark.django_db
def test_user_can_export_and_delete_account(client, user, vehicle):
    client.force_login(user)
    export_response = client.get(reverse("maintenance:account-export"))
    assert export_response.status_code == 200
    assert export_response.json()["vehicles"][0]["make"] == "Volvo"
    delete_response = client.post(reverse("maintenance:account-delete"))
    assert delete_response.status_code == 302
    assert not get_user_model().objects.filter(pk=user.pk).exists()


@pytest.mark.django_db
def test_transfer_can_be_accepted_by_new_user(client, user, vehicle):
    other_user = get_user_model().objects.create_user(
        username="buyer", password="Strong-test-password-123!"
    )
    transfer = Transfer.objects.create(
        vehicle=vehicle,
        from_user=user,
        expires_at=timezone.now() + timedelta(days=14),
    )
    client.force_login(other_user)
    response = client.post(reverse("maintenance:transfer-accept", args=[transfer.token]))
    assert response.status_code == 302
    transfer.refresh_from_db()
    assert transfer.to_user_id == other_user.pk
    assert transfer.status == Transfer.Status.ACCEPTED
    vehicle.refresh_from_db()
    assert vehicle.owner_id == other_user.pk


@pytest.mark.django_db
def test_public_transfer_does_not_expose_private_entries(client, user, vehicle):
    public_entry = MaintenanceEntry.objects.create(
        vehicle=vehicle,
        created_by=user,
        performed_on=date(2026, 1, 1),
        odometer_km=250000,
        category="oil",
        description="Publieke beurt",
        performed_by="self",
        visibility="public",
    )
    private_entry = MaintenanceEntry.objects.create(
        vehicle=vehicle,
        created_by=user,
        performed_on=date(2026, 1, 2),
        odometer_km=250100,
        category="other",
        description="Privé notitie",
        performed_by="self",
        visibility="private",
    )
    transfer = Transfer.objects.create(
        vehicle=vehicle,
        from_user=user,
        expires_at=timezone.now() + timedelta(days=14),
    )
    response = client.get(reverse("maintenance:transfer-public", args=[transfer.token]))
    assert response.status_code == 200
    assert public_entry.description in response.content.decode()
    assert private_entry.description not in response.content.decode()


@pytest.mark.django_db
def test_owner_can_create_a_read_only_share_link(client, user, vehicle):
    client.force_login(user)

    response = client.post(reverse("maintenance:share-create", args=[vehicle.pk]))

    share_link = ShareLink.objects.get(vehicle=vehicle)
    assert response.status_code == 302
    message = "".join(str(message) for message in messages.get_messages(response.wsgi_request))
    assert str(share_link.token) in message
    assert f'href="http://testserver/share/{share_link.token}/"' in message


@pytest.mark.django_db
def test_share_link_exposes_only_public_entries_without_transfer_action(client, user, vehicle, entry):
    public_entry = MaintenanceEntry.objects.create(
        vehicle=vehicle,
        created_by=user,
        performed_on=date(2026, 1, 2),
        odometer_km=250100,
        category="oil",
        description="Publieke onderhoudsbeurt",
        performed_by="garage",
        visibility="public",
    )
    share_link = ShareLink.objects.create(vehicle=vehicle, created_by=user)

    response = client.get(reverse("maintenance:share-public", args=[share_link.token]))

    content = response.content.decode()
    assert response.status_code == 200
    assert public_entry.description in content
    assert entry.description not in content
    assert "Dossier accepteren" not in content
    assert "Account maken" in content


@pytest.mark.django_db
def test_inactive_share_link_is_not_available(client, user, vehicle):
    share_link = ShareLink.objects.create(vehicle=vehicle, created_by=user, active=False)

    response = client.get(reverse("maintenance:share-public", args=[share_link.token]))

    assert response.status_code == 404


@pytest.mark.django_db
def test_signup_uses_local_console_email_backend(client, settings):
    settings.EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
    response = client.post(
        reverse("account_signup"),
        {
            "username": "new-user",
            "email": "new-user@example.com",
            "password1": "Strong-test-password-123!",
            "password2": "Strong-test-password-123!",
        },
    )
    assert response.status_code == 302
    assert get_user_model().objects.filter(username="new-user").exists()
    assert len(mail.outbox) == 1
    assert "new-user@example.com" in mail.outbox[0].to


@pytest.mark.django_db
@override_settings(DEBUG=False)
def test_unknown_url_shows_friendly_not_found_page(client):
    response = client.get("/pagina-die-niet-bestaat/")
    assert response.status_code == 404
    assert "Deze pagina bestaat niet." in response.content.decode()
    assert "Technical 404" not in response.content.decode()
