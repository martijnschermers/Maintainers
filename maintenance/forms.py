from django import forms

from .models import Attachment, MaintenanceEntry, PartUsed, Vehicle
from .services import format_license_plate


class VehicleForm(forms.ModelForm):
    rdw_lookup = forms.CharField(
        required=False,
        label="Kenteken opzoeken",
        widget=forms.TextInput(
            attrs={
                "placeholder": "Bijv. AB-12-CD",
                "class": "field uppercase",
                "data-rdw-lookup": "true",
            }
        ),
    )
    class Meta:
        model = Vehicle
        fields = [
            "vehicle_type",
            "make",
            "model",
            "year",
            "license_plate",
            "fuel_type",
            "current_odometer_km",
        ]
        labels = {
            "vehicle_type": "Voertuigtype",
            "make": "Merk",
            "model": "Model",
            "year": "Bouwjaar",
            "license_plate": "Kenteken",
            "fuel_type": "Brandstof",
            "current_odometer_km": "Huidige kilometerstand",
        }
        widgets = {
            field: forms.TextInput(
                attrs={"class": "field license-plate-input" if field == "license_plate" else "field"}
            )
            for field in ["make", "model", "year", "license_plate", "current_odometer_km"]
        }
        widgets.update(
            {
                "vehicle_type": forms.Select(
                    attrs={
                        "class": (
                            "w-full rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 "
                            "text-slate-100 outline-none transition focus:border-emerald-300 "
                            "focus:ring-2 focus:ring-emerald-300/20"
                        )
                    }
                ),
                "fuel_type": forms.Select(
                    attrs={
                        "class": (
                            "w-full rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 "
                            "text-slate-100 outline-none transition focus:border-emerald-300 "
                            "focus:ring-2 focus:ring-emerald-300/20"
                        )
                    }
                ),
            }
        )

    def clean_license_plate(self):
        license_plate = format_license_plate(self.cleaned_data["license_plate"])
        vehicles = Vehicle.objects.filter(license_plate=license_plate)
        if self.instance.pk:
            vehicles = vehicles.exclude(pk=self.instance.pk)
        if license_plate and vehicles.exists():
            raise forms.ValidationError("Dit kenteken is al aan een voertuig gekoppeld.")
        return license_plate


class MaintenanceEntryForm(forms.ModelForm):
    invoice_file = forms.FileField(
        required=False,
        label="Factuur voor analyse",
        widget=forms.ClearableFileInput(
            attrs={"accept": "image/*,.pdf", "class": "w-full file-input"}
        ),
    )

    class Meta:
        model = MaintenanceEntry
        fields = [
            "performed_on",
            "odometer_km",
            "category",
            "description",
            "performed_by",
            "total_cost",
            "notes",
            "trust_level",
            "visibility",
        ]
        labels = {
            "performed_on": "Datum uitgevoerd",
            "odometer_km": "Kilometerstand",
            "category": "Categorie",
            "description": "Omschrijving",
            "performed_by": "Uitgevoerd door",
            "total_cost": "Totale kosten",
            "notes": "Notities",
            "trust_level": "Vertrouwensniveau",
            "visibility": "Zichtbaarheid",
        }
        widgets = {
            "performed_on": forms.DateInput(
                format="%Y-%m-%d",
                attrs={"type": "date", "class": "field"},
            ),
            "odometer_km": forms.NumberInput(attrs={"class": "field"}),
            "category": forms.Select(attrs={"class": "field"}),
            "description": forms.Textarea(attrs={"rows": 4, "class": "field"}),
            "performed_by": forms.Select(attrs={"class": "field"}),
            "total_cost": forms.NumberInput(attrs={"class": "field", "step": "0.01"}),
            "notes": forms.Textarea(attrs={"rows": 3, "class": "field"}),
            "trust_level": forms.Select(attrs={"class": "field"}),
            "visibility": forms.Select(attrs={"class": "field"}),
        }

    def clean_invoice_file(self):
        uploaded_file = self.cleaned_data.get("invoice_file")
        if uploaded_file is None:
            return uploaded_file
        allowed_types = {"application/pdf", "image/jpeg", "image/png", "image/webp"}
        if uploaded_file.content_type not in allowed_types:
            raise forms.ValidationError("Upload alleen een PDF, JPEG, PNG of WebP-bestand.")
        if uploaded_file.size > 10 * 1024 * 1024:
            raise forms.ValidationError("Een bestand mag maximaal 10 MB groot zijn.")
        return uploaded_file


class PartUsedForm(forms.ModelForm):
    class Meta:
        model = PartUsed
        fields = ["description", "brand", "part_number", "quantity", "unit_price"]
        labels = {
            "description": "Onderdeel",
            "brand": "Merk",
            "part_number": "Onderdeelnummer",
            "quantity": "Aantal",
            "unit_price": "Prijs per stuk",
        }
        widgets = {
            "description": forms.TextInput(attrs={"class": "field"}),
            "brand": forms.TextInput(attrs={"class": "field"}),
            "part_number": forms.TextInput(attrs={"class": "field"}),
            "quantity": forms.NumberInput(attrs={"class": "field", "min": "1"}),
            "unit_price": forms.NumberInput(attrs={"class": "field", "min": "0", "step": "0.01"}),
        }


PartUsedFormSet = forms.inlineformset_factory(
    MaintenanceEntry,
    PartUsed,
    form=PartUsedForm,
    extra=1,
    can_delete=True,
)


class AttachmentForm(forms.ModelForm):
    class Meta:
        model = Attachment
        fields = ["file"]
        labels = {"file": "Foto of factuur"}
        widgets = {
            "file": forms.ClearableFileInput(
                attrs={"accept": "image/*,.pdf", "capture": "environment", "class": "file-input"}
            )
        }

    def clean_file(self):
        uploaded_file = self.cleaned_data["file"]
        allowed_types = {"application/pdf", "image/jpeg", "image/png", "image/webp"}
        max_size = 10 * 1024 * 1024
        if uploaded_file.content_type not in allowed_types:
            raise forms.ValidationError("Upload alleen een PDF, JPEG, PNG of WebP-bestand.")
        if uploaded_file.size > max_size:
            raise forms.ValidationError("Een bestand mag maximaal 10 MB groot zijn.")
        uploaded_file.seek(0)
        header = uploaded_file.read(12)
        uploaded_file.seek(0)
        signatures = {
            "application/pdf": header.startswith(b"%PDF"),
            "image/jpeg": header.startswith(b"\xff\xd8\xff"),
            "image/png": header.startswith(b"\x89PNG\r\n\x1a\n"),
            "image/webp": header[:4] == b"RIFF" and header[8:12] == b"WEBP",
        }
        if not signatures[uploaded_file.content_type]:
            raise forms.ValidationError("Het bestandstype komt niet overeen met de inhoud.")
        return uploaded_file
