# Maintainers

Het onderhoudsdossier dat bij het voertuig blijft.

## Status

Deze repository bevat de basis voor fase 0 van het implementatieplan:

- Django-monoliet met PostgreSQL-configuratie en lokale SQLite-fallback.
- Eerste datamodel voor voertuigen, eigenaarshistorie, onderhoud, bewijs, verificatie,
  overdracht en audit logging.
- Eerste gebruikersflow voor voertuigen: lijst, toevoegen, bewerken en verwijderen,
  met eigenaar-afgeschermde querysets.
- Dashboard, onderhoudstijdlijn, onderhoud toevoegen, overdrachtslink en publieke
  alleen-lezen dossierweergave.
- Accountloze, alleen-lezen deellinks voor gebruik in verkoopadvertenties.
- AI-factuuranalyse is achter een feature flag beschikbaar en standaard uitgeschakeld.
- Responsive TailwindCSS-styling via CDN voor landing page, dashboard en kernflows.
- Inloggen en registreren via django-allauth met Google- en Apple-provider.
- Foto's en facturen kunnen als PDF, JPEG, PNG of WebP aan onderhoudsentries worden toegevoegd;
  uploads worden server-side gevalideerd en voorzien van een SHA-256-hash.
- RDW-kentekenopzoeking, Chart.js-statistieken, CSV/PDF-export, account-export,
  accountverwijdering en overdracht accepteren zijn beschikbaar.
- Facturen kunnen met Google Document AI Invoice Parser worden geanalyseerd om het onderhoudsformulier voor te vullen;
  de gebruiker controleert de voorgestelde gegevens altijd vóór het opslaan.
- Django admin voor de handmatige validatiewachtrij.
- Docker Compose voor lokale ontwikkeling en Dokku `app.json`.
- CI voor checks, migraties, tests en linting.

De Google- en Apple-knoppen zijn technisch aangesloten. Vul de providergegevens in via `.env`
voordat je OAuth gebruikt. Gebruik in de providerconsole deze callback-URL's:

- Google: `http://localhost:8000/accounts/google/login/callback/`
- Apple: `http://localhost:8000/accounts/apple/login/callback/`

Voor productie vervang je `localhost:8000` door het HTTPS-domein. De Apple `client_secret`
moet een door Apple ondertekende client-secret JWT zijn; `APPLE_KEY_ID` is de bijbehorende
Key ID. Zet secrets uitsluitend in environment variables.

Voor factuuranalyse maak je in Google Cloud een Invoice Parser-processor aan en configureer je
`GOOGLE_CLOUD_PROJECT`, `GOOGLE_DOCUMENT_AI_LOCATION` en `GOOGLE_DOCUMENT_AI_PROCESSOR_ID`
in `.env`. Lokale ontwikkeling gebruikt Application Default Credentials via
`gcloud auth application-default login`; in productie gebruik je een service account.

Activeer hiervoor de Document AI API, maak in de Google Cloud Console een processor van het
type **Invoice Parser** aan en geef de gebruikte service account toegang tot Document AI.
Bijvoorbeeld voor lokale ontwikkeling:

```powershell
gcloud auth application-default login
gcloud auth application-default set-quota-project JOUW_PROJECT_ID
```

De processornaam mag ook rechtstreeks via `GOOGLE_DOCUMENT_AI_PROCESSOR_NAME` worden
ingesteld. Deze heeft de vorm
`projects/PROJECT_ID/locations/eu/processors/PROCESSOR_ID`.

Zet `FEATURE_INVOICE_ANALYSIS_ENABLED=1` om de AI-factuuranalyse te activeren. De MVP kan
deze instelling op `0` laten staan; facturen kunnen dan nog steeds als bewijsstuk worden
geüpload.

### E-mail lokaal testen

Zonder `EMAIL_HOST` gebruikt Django de console-backend. Registratie werkt dan lokaal en
bevestigingsmails verschijnen in de terminal van de webcontainer:

```powershell
docker compose logs -f web
```

Voor echte e-mails vul je `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`,
`EMAIL_HOST_PASSWORD` en `DEFAULT_FROM_EMAIL` in `.env` in. Herstart daarna de webcontainer:

```powershell
docker compose up -d --build web
```

## Lokaal starten

Vereist: Python 3.12+ en Docker Desktop.

```powershell
Copy-Item .env.example .env
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

## Migraties uitvoeren

Voer migraties uit op dezelfde omgeving/database waarop de applicatie draait.

### Lokaal met SQLite

```powershell
python manage.py migrate
```

### Docker Compose

Start eerst de database en webcontainer:

```powershell
docker compose up -d db web
docker compose exec web python manage.py migrate
```

Als de webcontainer nog niet draait, gebruik dan:

```powershell
docker compose run --rm web python manage.py migrate
```

De migratie van `django.contrib.sites` maakt onder andere de tabel `django_site`
aan die django-allauth gebruikt.

### Dokku

```bash
dokku postgres:link <database> <app>
dokku run <app> python manage.py migrate --noinput
```

Voor PostgreSQL:

```powershell
docker compose up --build
```

De admin is beschikbaar op <http://localhost:8000/admin/> en de healthcheck op
<http://localhost:8000/health/>.

## Checks

```powershell
python manage.py check
python manage.py makemigrations --check --dry-run
pytest
ruff check .
```

### Pre-commit hooks

Installeer de hooks eenmalig na het installeren van de requirements:

```powershell
pre-commit install
```

Bij elke commit worden de statische bestanden verzameld en draait de volledige test suite.
Je kunt de hooks handmatig voor alle bestanden uitvoeren met:

```powershell
pre-commit run --all-files
```
