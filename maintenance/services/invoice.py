import logging
import os
import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

from django.core.exceptions import ValidationError
from google.api_core.client_options import ClientOptions
from google.api_core.exceptions import GoogleAPICallError
from google.auth.exceptions import GoogleAuthError
from google.cloud import documentai_v1

from ..models.entries import round_money

logger = logging.getLogger(__name__)

INVOICE_CATEGORIES = {
    "oil": ("olie", "motorolie", "vloeistof"),
    "brakes": ("rem", "remblok", "remschijf"),
    "tires": ("band", "banden", "wiel"),
    "engine": ("motor", "distributie", "bougie"),
    "electrical": ("accu", "batterij", "lamp", "elektrisch"),
    "body": ("carrosserie", "lak", "ruit", "spiegel"),
    "inspection": ("apk", "inspectie", "onderhoudsbeurt", "keuring"),
}


def analyze_invoice(uploaded_file):
    project, location, processor_id = _processor_config()
    content = uploaded_file.read()
    uploaded_file.seek(0)
    mime_type = uploaded_file.content_type or "application/octet-stream"
    if mime_type not in {"application/pdf", "image/jpeg", "image/png", "image/webp"}:
        raise ValidationError("Upload alleen een PDF, JPEG, PNG of WebP-bestand.")

    try:
        client_options = (
            ClientOptions(api_endpoint=f"{location}-documentai.googleapis.com")
            if location != "us"
            else None
        )
        client = documentai_v1.DocumentProcessorServiceClient(client_options=client_options)
        processor_name = client.processor_path(project, location, processor_id)
        processor = client.get_processor(request=documentai_v1.GetProcessorRequest(name=processor_name))
        result = client.process_document(
            request=documentai_v1.ProcessRequest(
                name=processor.name,
                raw_document=documentai_v1.RawDocument(content=content, mime_type=mime_type),
            )
        )
    except (GoogleAPICallError, GoogleAuthError) as error:
        logger.exception(
            "Google Document AI invoice analysis failed (mime_type=%s, processor_location=%s)",
            mime_type,
            processor_name.split("/locations/")[-1].split("/")[0],
        )
        raise ValidationError("De factuuranalyse via Google Document AI is mislukt.") from error

    return _map_invoice_result(result.document)


def _processor_config():
    configured_name = _env("GOOGLE_DOCUMENT_AI_PROCESSOR_NAME")
    if configured_name:
        match = re.fullmatch(
            r"projects/(?P<project>[^/]+)/locations/(?P<location>[^/]+)/processors/(?P<processor>[^/]+)",
            configured_name,
        )
        if not match:
            raise ValidationError("GOOGLE_DOCUMENT_AI_PROCESSOR_NAME heeft een ongeldig formaat.")
        return match.group("project"), match.group("location"), match.group("processor")
    project = _env("GOOGLE_CLOUD_PROJECT")
    location = _env("GOOGLE_DOCUMENT_AI_LOCATION", "eu")
    processor_id = _env("GOOGLE_DOCUMENT_AI_PROCESSOR_ID")
    if not project or not processor_id:
        raise ValidationError(
            "Factuuranalyse is niet ingesteld: configureer GOOGLE_CLOUD_PROJECT en "
            "GOOGLE_DOCUMENT_AI_PROCESSOR_ID."
        )
    return project, location, processor_id


def _env(name, default=""):
    return os.getenv(name, default).strip()


def _map_invoice_result(document):
    entities = list(document.entities)
    text = document.text or ""
    line_items = _line_items(entities)
    descriptions = [item["description"] for item in line_items]
    description = "; ".join(descriptions) or "Onderhoud volgens factuur"
    performed_on = _parse_date(_first_entity_value(entities, "invoice_date", "purchase_date"))
    odometer_km = _parse_odometer(text)
    parts_total = _parts_total(line_items)
    total_cost = parts_total or _entity_amount(entities, "total_amount", "net_amount") or _amount_from_text(text)
    category = _category_for_text(f"{description} {text}")
    notes = _invoice_note(entities)
    return {
        "performed_on": performed_on.isoformat() if performed_on else "",
        "odometer_km": odometer_km or "",
        "category": category,
        "description": description,
        "parts": line_items,
        "performed_by": "garage",
        "total_cost": str(round_money(total_cost)) if total_cost is not None else "0.00",
        "currency": "EUR",
        "notes": notes,
        "trust_level": "self_reported",
        "visibility": "private",
    }


def _first_entity_value(entities, *keys):
    return next(
        (entity.mention_text.strip() for entity in entities if entity.type_ in keys and entity.mention_text),
        "",
    )


def _line_item_descriptions(entities):
    descriptions = []
    for entity in entities:
        if entity.type_ in {"line_item", "line_item/description"}:
            if entity.type_ == "line_item/description" and entity.mention_text:
                descriptions.append(entity.mention_text.strip())
            for property_entity in getattr(entity, "properties", []):
                if property_entity.type_.split("/")[-1] == "description" and property_entity.mention_text:
                    descriptions.append(property_entity.mention_text.strip())
    return list(dict.fromkeys(description for description in descriptions if not _is_personal_text(description)))


def _line_items(entities):
    items = []
    for entity in entities:
        if entity.type_ == "line_item":
            properties = [
                property_entity
                for property_entity in getattr(entity, "properties", [])
                if property_entity.mention_text
            ]
            descriptions = [item.mention_text.strip() for item in properties if item.type_.endswith("/description")]
            for description in descriptions:
                if _is_personal_text(description) or _is_non_part_cost(description):
                    continue
                quantity = next((item.mention_text for item in properties if item.type_.endswith("/quantity")), "")
                unit_price = next(
                    (item.mention_text for item in properties if item.type_.endswith("/unit_price")),
                    "",
                )
                items.append(
                    {
                        "description": description,
                        "brand": next(
                            (item.mention_text for item in properties if item.type_.endswith("/brand")),
                            "",
                        ),
                        "part_number": next(
                            (item.mention_text for item in properties if item.type_.endswith("/part_number")),
                            "",
                        ),
                        "quantity": _parse_quantity(quantity) or 1,
                        "unit_price": str(round_money(_parse_amount(unit_price) or 0)),
                    }
                )
        elif entity.type_ == "line_item/description" and entity.mention_text:
            description = entity.mention_text.strip()
            if not _is_personal_text(description) and not _is_non_part_cost(description):
                items.append(
                    {
                        "description": description,
                        "brand": "",
                        "part_number": "",
                        "quantity": 1,
                        "unit_price": "0",
                    }
                )
    return items


def _parts_total(items):
    return round_money(sum(
        Decimal(item["quantity"]) * Decimal(item["unit_price"])
        for item in items
        if Decimal(item["unit_price"]) > 0
    ))


def _is_non_part_cost(value):
    normalized = value.lower()
    return any(keyword in normalized for keyword in ("verzend", "shipping", "transportkosten", "bezorgkosten"))


def _parse_quantity(value):
    match = re.search(r"\d+", value or "")
    return int(match.group()) if match else None


def _is_personal_text(value):
    normalized = " ".join(value.split())
    lowered = normalized.lower()
    return bool(
        re.search(r"\b\d{4}\s?[a-z]{2}\b", lowered)
        or re.search(r"\b(?:naam|adres|woonplaats|postcode|telefoon|tel|e-mail|email)\b", lowered)
        or re.search(r"\b(?:straat|str\.|laan|weg|plein|singel|dreef|kade)\b", lowered)
        or re.search(r"\b\d{1,4}[a-z]?\s+\w+", lowered)
        or "@" in lowered
    )


def _entity_amount(entities, *keys):
    for entity in entities:
        if entity.type_ not in keys:
            continue
        normalized_value = getattr(entity, "normalized_value", None)
        money_value = getattr(normalized_value, "money_value", None)
        if money_value:
            units = Decimal(str(getattr(money_value, "units", 0)))
            nanos = Decimal(str(getattr(money_value, "nanos", 0))) / Decimal("1000000000")
            return units + nanos
        amount = _parse_amount(getattr(entity, "mention_text", ""))
        if amount is not None:
            return amount
    return None


def _amount_from_text(text):
    matches = re.findall(
        r"(?i)(?:totaal(?:bedrag)?|te betalen|grand total)[^\d€]{0,20}(€?\s*[\d.]+(?:,\d{2})?)",
        text,
    )
    return _parse_amount(matches[-1]) if matches else None


def _parse_date(value):
    if not value:
        return None
    for pattern in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%d.%m.%Y"):
        try:
            return date.fromisoformat(value) if pattern == "%Y-%m-%d" else datetime.strptime(value, pattern).date()
        except ValueError:
            continue
    return None


def _parse_odometer(text):
    match = re.search(r"(?i)(?:kilometerstand|km[-\s]?stand|odometer)[^\d]{0,20}([\d. ]{3,})\s*km?", text)
    if not match:
        return None
    digits = re.sub(r"\D", "", match.group(1))
    return int(digits) if digits else None


def _parse_amount(value):
    if not value:
        return None
    normalized = re.sub(r"[^\d,.-]", "", value)
    if "," in normalized:
        normalized = normalized.replace(".", "").replace(",", ".")
    try:
        return Decimal(normalized)
    except InvalidOperation:
        return None


def _category_for_text(text):
    lowered = text.lower()
    for category, keywords in INVOICE_CATEGORIES.items():
        if any(keyword in lowered for keyword in keywords):
            return category
    return "other"


def _invoice_note(entities):
    invoice_id = _first_entity_value(entities, "invoice_id")
    supplier = _first_entity_value(entities, "supplier_name")
    details = []
    if supplier:
        details.append(f"Leverancier: {supplier}")
    if invoice_id:
        details.append(f"Factuurnummer: {invoice_id}")
    return " · ".join(details)
