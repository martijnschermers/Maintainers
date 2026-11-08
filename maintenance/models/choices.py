from django.db import models


class VehicleType(models.TextChoices):
    CAR = "car", "Auto"
    MOTORCYCLE = "motorcycle", "Motor"
    TRUCK = "truck", "Vrachtwagen"
    SCOOTER = "scooter", "Scooter"
    MOPED = "moped", "Bromfiets"


class FuelType(models.TextChoices):
    PETROL = "petrol", "Benzine"
    DIESEL = "diesel", "Diesel"
    HYBRID = "hybrid", "Hybride"
    ELECTRIC = "electric", "Elektrisch"
    LPG = "lpg", "LPG"
    OTHER = "other", "Anders"


class MaintenanceCategory(models.TextChoices):
    OIL = "oil", "Olie en vloeistoffen"
    BRAKES = "brakes", "Remmen"
    TIRES = "tires", "Banden"
    ENGINE = "engine", "Motor"
    ELECTRICAL = "electrical", "Elektrisch"
    BODY = "body", "Carrosserie"
    INSPECTION = "inspection", "Onderhoudsbeurt"
    OTHER = "other", "Overig"


class TrustLevel(models.TextChoices):
    SELF_REPORTED = "self_reported", "Zelf gerapporteerd"
    EVIDENCE = "evidence", "Met bewijs"
    REVIEWED = "reviewed", "Gecontroleerd"
    THIRD_PARTY = "third_party", "Bevestigd door derde"


class Visibility(models.TextChoices):
    PRIVATE = "private", "Privé"
    PUBLIC = "public", "Publiek"
