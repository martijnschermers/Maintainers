import django.core.validators
import django.db.models.deletion
import uuid
from decimal import Decimal

from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = [migrations.swappable_dependency(settings.AUTH_USER_MODEL)]

    operations = [
        migrations.CreateModel(
            name="Vehicle",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("vehicle_type", models.CharField(choices=[("car", "Auto"), ("motorcycle", "Motor"), ("truck", "Vrachtwagen")], default="car", max_length=20)),
                ("make", models.CharField(max_length=100, verbose_name="merk")),
                ("model", models.CharField(max_length=100)),
                ("year", models.PositiveSmallIntegerField(blank=True, null=True)),
                ("license_plate", models.CharField(blank=True, max_length=12)),
                ("vin", models.CharField(blank=True, max_length=17)),
                ("fuel_type", models.CharField(blank=True, choices=[("petrol", "Benzine"), ("diesel", "Diesel"), ("hybrid", "Hybride"), ("electric", "Elektrisch"), ("lpg", "LPG"), ("other", "Anders")], max_length=20)),
                ("current_odometer_km", models.PositiveIntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("owner", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="vehicles", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["make", "model"]},
        ),
        migrations.CreateModel(
            name="Ownership",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("from_date", models.DateField()),
                ("until_date", models.DateField(blank=True, null=True)),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="ownerships", to=settings.AUTH_USER_MODEL)),
                ("vehicle", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="ownerships", to="maintenance.vehicle")),
            ],
            options={"ordering": ["-from_date"]},
        ),
        migrations.CreateModel(
            name="MaintenanceEntry",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("performed_on", models.DateField()),
                ("odometer_km", models.PositiveIntegerField()),
                ("category", models.CharField(choices=[("oil", "Olie en vloeistoffen"), ("brakes", "Remmen"), ("tires", "Banden"), ("engine", "Motor"), ("electrical", "Elektrisch"), ("body", "Carrosserie"), ("inspection", "Onderhoudsbeurt"), ("other", "Overig")], max_length=20)),
                ("description", models.TextField()),
                ("performed_by", models.CharField(choices=[("self", "Zelf"), ("garage", "Garage")], max_length=20)),
                ("total_cost", models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=10, validators=[django.core.validators.MinValueValidator(Decimal("0"))])),
                ("currency", models.CharField(default="EUR", max_length=3)),
                ("notes", models.TextField(blank=True)),
                ("trust_level", models.CharField(choices=[("self_reported", "Zelf gerapporteerd"), ("evidence", "Met bewijs"), ("reviewed", "Gecontroleerd"), ("third_party", "Bevestigd door derde")], default="self_reported", max_length=20)),
                ("visibility", models.CharField(choices=[("private", "Privé"), ("public", "Publiek")], default="private", max_length=10)),
                ("version", models.PositiveIntegerField(default=1)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("created_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL)),
                ("supersedes", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="superseding_entries", to="maintenance.maintenanceentry")),
                ("vehicle", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="maintenance_entries", to="maintenance.vehicle")),
            ],
            options={"ordering": ["-performed_on", "-odometer_km"]},
        ),
        migrations.CreateModel(
            name="Attachment",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("file", models.FileField(upload_to="maintenance/%Y/%m/")),
                ("content_type", models.CharField(max_length=100)),
                ("sha256", models.CharField(editable=False, max_length=64)),
                ("uploaded_at", models.DateTimeField(auto_now_add=True)),
                ("entry", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="attachments", to="maintenance.maintenanceentry")),
                ("uploaded_by", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name="PartUsed",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("brand", models.CharField(blank=True, max_length=100)),
                ("part_number", models.CharField(blank=True, max_length=100)),
                ("quantity", models.PositiveIntegerField(default=1)),
                ("unit_price", models.DecimalField(decimal_places=2, max_digits=10, validators=[django.core.validators.MinValueValidator(Decimal("0"))])),
                ("entry", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="parts", to="maintenance.maintenanceentry")),
            ],
        ),
        migrations.CreateModel(
            name="Transfer",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("token", models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ("status", models.CharField(choices=[("open", "Open"), ("accepted", "Geaccepteerd"), ("expired", "Verlopen"), ("rejected", "Geweigerd")], default="open", max_length=10)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("expires_at", models.DateTimeField()),
                ("accepted_at", models.DateTimeField(blank=True, null=True)),
                ("from_user", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="outgoing_transfers", to=settings.AUTH_USER_MODEL)),
                ("to_user", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, related_name="incoming_transfers", to=settings.AUTH_USER_MODEL)),
                ("vehicle", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="transfers", to="maintenance.vehicle")),
            ],
        ),
        migrations.CreateModel(
            name="Verification",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("method", models.CharField(choices=[("backoffice", "Backoffice"), ("ai", "AI")], max_length=20)),
                ("outcome", models.CharField(choices=[("approved", "Goedgekeurd"), ("rejected", "Afgewezen"), ("needs_review", "Nader onderzoek")], max_length=20)),
                ("explanation", models.TextField()),
                ("model_name", models.CharField(blank=True, max_length=100)),
                ("model_version", models.CharField(blank=True, max_length=100)),
                ("checked_at", models.DateTimeField(auto_now_add=True)),
                ("checked_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL)),
                ("entry", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="verifications", to="maintenance.maintenanceentry")),
            ],
        ),
        migrations.CreateModel(
            name="AuditLog",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("action", models.CharField(max_length=100)),
                ("object_type", models.CharField(max_length=100)),
                ("object_id", models.PositiveBigIntegerField()),
                ("payload", models.JSONField(default=dict)),
                ("previous_hash", models.CharField(blank=True, max_length=64)),
                ("record_hash", models.CharField(editable=False, max_length=64)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("actor", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL)),
                ("vehicle", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="audit_logs", to="maintenance.vehicle")),
            ],
        ),
        migrations.AddConstraint(model_name="vehicle", constraint=models.CheckConstraint(condition=models.Q(("current_odometer_km__gte", 0)), name="vehicle_odometer_nonnegative")),
        migrations.AddConstraint(model_name="vehicle", constraint=models.UniqueConstraint(condition=~models.Q(("vin", "")), fields=("vin",), name="unique_nonempty_vehicle_vin")),
        migrations.AddConstraint(model_name="ownership", constraint=models.CheckConstraint(condition=models.Q(("until_date__isnull", True)) | models.Q(("until_date__gte", models.F("from_date"))), name="ownership_until_after_from")),
        migrations.AddConstraint(model_name="ownership", constraint=models.UniqueConstraint(fields=("vehicle", "user", "from_date"), name="unique_vehicle_user_start_date")),
        migrations.AddConstraint(model_name="maintenanceentry", constraint=models.CheckConstraint(condition=models.Q(("total_cost__gte", 0)), name="maintenance_cost_nonnegative")),
        migrations.AddConstraint(model_name="partused", constraint=models.CheckConstraint(condition=models.Q(("quantity__gt", 0)), name="part_quantity_positive")),
        migrations.AddConstraint(model_name="partused", constraint=models.CheckConstraint(condition=models.Q(("unit_price__gte", 0)), name="part_price_nonnegative")),
    ]
