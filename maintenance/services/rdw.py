import requests
from django.core.exceptions import ValidationError

from .plates import format_license_plate

RDW_URL = "https://opendata.rdw.nl/resource/m9d7-ebf2.json"


def lookup_rdw_license_plate(license_plate):
    normalized = "".join(license_plate.upper().split()).replace("-", "")
    if not normalized:
        raise ValidationError("Vul een kenteken in.")
    response = requests.get(RDW_URL, params={"kenteken": normalized}, timeout=5)
    response.raise_for_status()
    records = response.json()
    if not records:
        raise ValidationError("Geen voertuig gevonden voor dit kenteken.")
    record = records[0]
    return {
        "license_plate": format_license_plate(normalized),
        "make": _sentence_case_vehicle_text(record.get("merk", "")),
        "model": _sentence_case_vehicle_text(record.get("handelsbenaming", "")),
        "year": int(record["datum eerste toelating"][:4]) if record.get("datum eerste toelating") else None,
        "fuel_type": _fuel_type(record.get("brandstof_omschrijving", "")),
    }


def _fuel_type(value):
    value = value.lower()
    if "diesel" in value:
        return "diesel"
    if "elektr" in value:
        return "electric"
    if "lpg" in value:
        return "lpg"
    if "hybr" in value:
        return "hybrid"
    if "benz" in value:
        return "petrol"
    return "other" if value else ""


def _sentence_case_vehicle_text(value):
    return " ".join(word[:1].upper() + word[1:].lower() for word in value.split())
