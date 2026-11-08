# Maintainers – implementatieplan

*Het onderhoudsdossier dat bij het voertuig blijft. Een plan voor MVP, architectuur en uitrol.*

## 1. Samenvatting

Maintainers is een website waarmee DIY'ers het onderhoud aan hun voertuig vastleggen en dat dossier kunnen overdragen aan een volgende eigenaar. De kern van de waarde zit niet in het *bijhouden* (dat doen meer apps), maar in **betrouwbaarheid en overdraagbaarheid**: een koper moet het dossier kunnen vertrouwen.

**Advies in het kort**

- Bouw een **Django-monoliet** (server-rendered met HTMX) op **PostgreSQL**, gedraaid via **Docker + Dokku** op één server.
- Gebruik **django-allauth** voor inloggen (e-mail, Google, Apple) in plaats van de zelfgebouwde login.
- Modelleer onderhoud als **append-only gebeurtenissen met een vertrouwensniveau** in plaats van een simpel "gevalideerd ja/nee".
- Start met een **handmatige validatie (backoffice)** en voeg AI-ondersteuning toe als hulpmiddel, niet als beslisser.
- Begin met **auto's**; ontwerp het datamodel wel generiek zodat motor en vrachtwagen later weinig werk zijn.

## 2. Uitgangspunten en afbakening

- **Doelgroep:** DIY'ers met één tot enkele voertuigen. Geen vlootbeheer, geen garage-workflows.
- **Platform:** website (responsive), geen native app. Camera via de browser volstaat (zie 5.6).
- **Geen scope in MVP:** onderhoudsherinneringen via push, garage-integraties, vlootfuncties, native apps.

## 3. Technische keuzes

| Onderdeel | Aanbeveling | Alternatief / opmerking |
| --- | --- | --- |
| Backend | Django (Python) | Past bij je voorkeur en Dokku-ervaring |
| Front-end | Django-templates + HTMX + Alpine.js | React/Next.js alleen als je later zware interactiviteit nodig hebt; dubbele codebase kost tijd |
| Styling | Tailwind CSS | of Bootstrap voor snelheid |
| Grafieken | Apache ECharts of Chart.js | Beide werken goed zonder SPA |
| Database | PostgreSQL | Sterke typering, constraints, JSONB voor flexibele velden |
| Auth | django-allauth (Google, Apple, e-mail) | Extern: Keycloak, Authentik of Auth0 als je SSO buiten Django wilt |
| Achtergrondtaken | Celery + Redis, of lichter: Huey / Django-Q2 | Nodig voor OCR, e-mail, thumbnails |
| Bestandsopslag | S3-compatibele opslag (bijv. Hetzner Object Storage, MinIO) | Niet op de app-server zelf, voor back-ups en schaalbaarheid |
| API | Django REST Framework (later) | Pas toevoegen bij behoefte aan app of integraties |
| Hosting | Eén VPS met Dokku (zie hoofdstuk 7) | Managed als tijd belangrijker is dan geld |

**Waarom HTMX in plaats van een SPA?** Eén codebase, snel opleveren, goede SEO, minder te onderhouden. Voor formulieren, tabellen en grafieken is het ruim voldoende.

## 4. Datamodel (eerste opzet)

Het datamodel is het hart van het project. Principes:

- **Geld:** `DecimalField` (of `django-money`), nooit floats. Sla valuta op bij elk bedrag.
- **Afstand/kilometerstand:** sla intern altijd op in **kilometers** (integer of decimal) en bewaar de oorspronkelijke eenheid (km/mi) apart voor weergave.
- **Tijd:** `DateField` voor onderhoudsdatum, `DateTimeField` (UTC) voor aanmaak en wijziging.
- **Voertuigtypen:** één `Vehicle`-tabel met `type` (auto, motor, vrachtwagen, enz.) in plaats van losse tabellen per type.

**Kernentiteiten**

- **User**: account, e-mail, aanmaakdatum.
- **Vehicle**: type, merk, model, bouwjaar, kenteken, VIN/chassisnummer, brandstoftype, huidige kilometerstand.
- **Ownership**: koppeling gebruiker ↔ voertuig met `van` en `tot` datum. Zo is de eigenaarshistorie vast te leggen en kan een overdracht netjes worden afgesloten.
- **MaintenanceEntry**: voertuig, datum, kilometerstand, categorie (olie, remmen, banden, enz.), omschrijving, uitgevoerd door (zelf / garage), totale kosten, notities, vertrouwensniveau, zichtbaarheid.
- **PartUsed**: onderdeel bij een entry (merk, artikelnummer, aantal, prijs).
- **Attachment**: foto's, facturen, bonnen, met bestandstype, hash en uploader.
- **Verification**: wie of wat heeft gecontroleerd (AI of backoffice), uitkomst, toelichting, tijdstip.
- **Transfer**: overdrachtsverzoek met token, status (open, geaccepteerd, verlopen, geweigerd), van- en naar-gebruiker.
- **AuditLog**: onveranderlijke registratie van wijzigingen (zie 5.3).

**Aandachtspunten**

- Voeg **constraints** toe: kilometerstand mag in de tijd niet dalen zonder expliciete correctie, kosten mogen niet negatief zijn.
- Gebruik een gestandaardiseerde **categorielijst** (niet alleen vrije tekst), anders zijn grafieken en vergelijking lastig.
- Een `VehicleOdometerReading`-tabel (los van onderhoud) maakt grafieken over kilometerstand en gebruik per jaar eenvoudig.

## 5. Extra suggesties

### 5.1 Kenteken opzoeken

Voor Nederlandse voertuigen kun je via de **open data van de RDW** merk, model, bouwjaar, brandstof en APK-vervaldatum automatisch invullen. Dat scheelt invoer en verkleint typefouten. Maak dit modulair, zodat je later andere landen kunt toevoegen.

### 5.2 Vertrouwensniveaus in plaats van ja/nee

Een simpel "gevalideerd" is te grof. Gebruik bijvoorbeeld:

1. **Zelf gerapporteerd**: alleen tekst.
2. **Met bewijs**: foto van werk, onderdeel of bon toegevoegd.
3. **Gecontroleerd**: bon/factuur door AI of backoffice gecontroleerd (datum, bedrag, onderdelen, voertuig komen overeen).
4. **Bevestigd door derde**: een garage of vorige eigenaar bevestigt (later).

Dit is eerlijker richting kopers en geeft DIY'ers die geen factuur hebben (eigen werk) toch een plek.

### 5.3 Onveranderlijkheid en audit trail

Om de integriteit aan te tonen: maak entries **append-only** (wijzigen = nieuwe versie, oude blijft zichtbaar) en bewaar een **hash** van elke bijlage. Overweeg een hash-keten per voertuig, zodat achteraf aanpassen opvalt. Dit is een sterk verkoopargument voor een overdraagbaar dossier.

### 5.4 Overdrachtsflow

- Verkoper start overdracht, kiest wat wordt overgedragen (alles, of alleen publieke entries).
- Koper ontvangt een link of code, maakt een account (of logt in) en accepteert.
- De oude eigenaar behoudt eventueel een **alleen-lezen kopie** of anonimiseert persoonlijke notities, afhankelijk van je keuze.
- Bied een **deelbare, alleen-lezen link of PDF-rapport** aan voor kopers die nog geen account hebben (bijvoorbeeld bij een verkoopadvertentie). Dit is ook een goede groeikans.

### 5.5 Privacy en AVG

- Facturen bevatten vaak naam, adres en kenteken. Laat gebruikers **gevoelige delen afschermen** of markeren.
- Leg vast welke persoonsgegevens je bewaart, hoe lang, en hoe iemand zijn account en data kan verwijderen of exporteren.
- Als je AI-diensten gebruikt voor OCR: let op **waar data wordt verwerkt** en of de leverancier je data voor training gebruikt. Kies bij voorkeur een EU-verwerking of zelf gehoste oplossing.

### 5.6 Camera op een website

De browser kan prima foto's maken: een `<input type="file" accept="image/*" capture="environment">` opent op mobiel direct de camera. Combineer dit met een **PWA** (installeerbaar op het beginscherm) voor een app-achtige ervaring zonder native app. Voeg client-side beeldverkleining toe om uploads klein te houden.

### 5.7 Grafieken die echt waarde geven

- Kosten per jaar en per categorie.
- Kosten per kilometer.
- Kilometerstand over tijd (en gemiddeld per jaar).
- Tijdlijn van onderhoud met onderhoudsintervallen en "te laat"-indicatoren.
- Totale kosten van eigendom (aanschaf, onderhoud, later eventueel brandstof).

### 5.8 Onderhoudsschema's

Bied per type voertuig een **standaardschema** (bijv. olie elke 15.000 km of jaarlijks) dat de gebruiker kan aanpassen. Dit maakt het product dagelijks bruikbaar en geeft aanleiding om terug te komen.

### 5.9 Data-import en -export

CSV-import (bijvoorbeeld vanuit andere apps of Excel) verlaagt de drempel om over te stappen. Export (CSV/PDF) bouwt vertrouwen en past bij een open-source gedachte.

## 6. Validatie van onderhoud (aanpak)

**Fase A – handmatig (MVP)**

- Gebruiker uploadt foto's van bon of factuur bij een entry.
- Backoffice-medewerker (jijzelf in het begin) controleert in een eenvoudige admin-weergave en zet het vertrouwensniveau.
- Gebruik de **Django admin** met een aangepaste wachtrij; geen aparte backoffice-applicatie bouwen.

**Fase B – AI als assistent**

- OCR/vision-model leest datum, bedrag, leverancier, onderdelen en voertuiggegevens uit de foto.
- Het systeem vergelijkt met wat de gebruiker invulde en markeert afwijkingen.
- Bij hoge overeenkomst: automatisch "gecontroleerd door AI"; bij twijfel: naar de backoffice-wachtrij.
- Log altijd welk model en welke versie een uitspraak deed.

**Fraudesignalen om te detecteren (later)**

- Hergebruik van dezelfde bon bij meerdere voertuigen (via bestandshash).
- Metadata die niet klopt (bewerkte afbeelding, datum in de toekomst).
- Kilometerstand die niet past in de tijdlijn.

Wees open over de grenzen: AI-validatie toont aan dat een **document consistent is**, niet dat het werk daadwerkelijk is uitgevoerd. Communiceer dit duidelijk in de interface.

## 7. Hosting en infrastructuur

**Aanbeveling voor start:** één VPS (bijvoorbeeld Hetzner, EU) met **Dokku**.

- Dokku-plugins: PostgreSQL, Redis, Let's Encrypt voor HTTPS.
- Deploy via `git push`; houd Dockerfile en `app.json` in de repository.
- **Back-ups:** dagelijkse `pg_dump` naar externe objectopslag, met **geteste restore** (plan een herstelproef in).
- **Monitoring:** Uptime Kuma (uptime), Sentry (fouten), eenvoudige logaggregatie.
- Bestanden van gebruikers in object storage, niet op de VPS-schijf.

**Zelf hosten vs. managed**

|  | Zelf (VPS + Dokku) | Managed (bijv. PaaS + beheerde database) |
| --- | --- | --- |
| Kosten | Laag | Hoger |
| Beheerlast | Jij: updates, beveiliging, back-ups | Gering |
| Flexibiliteit | Hoog | Beperkt door platform |
| Schaalbaarheid | Handmatig | Eenvoudiger |

Advies: begin zelf met Dokku (je kent het al), maar neem de **database en back-ups** serieus. Verlies van onderhoudsdossiers is het ergste wat het product kan overkomen. Overweeg een **managed PostgreSQL** zodra er echte gebruikers zijn.

## 8. Open source en verdienmodel

- **Licentie:** AGPL beschermt tegen commerciële kopieën die niets teruggeven; MIT/Apache is vriendelijker maar maakt kopiëren makkelijker.
- **Open core:** de basis is open; betaalde extra's zijn bijvoorbeeld gehoste versie, AI-validatie, PDF-rapporten, verkoopcertificaat en onbeperkte opslag.
- **Betaalmodellen om te onderzoeken:**
  - Gratis tot X voertuigen/opslag, daarna abonnement.
  - Eenmalige betaling voor een **geverifieerd overdrachtsdossier** (verkoper betaalt, koper krijgt vertrouwen).
  - Samenwerking met occasiondealers of keuringsstations (later).
- **Let op:** self-hosting en gehoste dienst concurreren. Houd de waarde in de dienst (validatie, vertrouwen, netwerk), niet alleen in de code.
- Beslis dit **vóór** je publiceert; een licentie achteraf wijzigen is lastig.

## 9. Faseringsplan

De tijdsinschatting gaat uit van één ontwikkelaar die deeltijds werkt; pas aan op je beschikbare uren.

### Fase 0 – Fundament (1–2 weken)

- Beslissingen vastleggen: licentie (voorlopig), stack, naam en domein.
- Repository, Docker-opzet, CI (tests, lint), Dokku-deploy naar een staging-omgeving.
- Datamodel uitwerken en reviewen; wireframes voor de kernschermen.
- **Resultaat:** lege app draait op staging, datamodel staat.

### Fase 1 – Accounts en voertuigen (2 weken)

- Authenticatie via django-allauth (e-mail + Google, daarna Apple).
- Migratie van bestaande gebruikers van de zelfgebouwde login (indien aanwezig).
- Voertuig toevoegen, bewerken, verwijderen; ondersteuning voor de drie voertuigtypen op datamodelniveau.
- RDW-kentekenopzoeking voor NL.
- **Resultaat:** gebruiker kan inloggen en voertuigen beheren.

### Fase 2 – Onderhoud vastleggen (2–3 weken)

- Onderhoudsentries met categorie, kosten, kilometerstand, onderdelen.
- Bijlagen uploaden (foto's, facturen) naar objectopslag.
- Tijdlijnweergave per voertuig.
- Basisgrafieken: kosten per jaar/categorie, kilometerstand over tijd.
- **Resultaat:** het kernproduct is bruikbaar voor eigen gebruik.

### Fase 3 – Validatie, versie 1 (2 weken)

- Vertrouwensniveaus en statusweergave.
- Backoffice-wachtrij in Django admin voor handmatige controle.
- Audit trail en bestandshashes.
- **Resultaat:** entries kunnen worden gecontroleerd en gemarkeerd.

### Fase 4 – Overdracht (2 weken)

- Eigenaarshistorie (Ownership) en overdrachtsflow met uitnodigingslink.
- Alleen-lezen deelbare link en PDF-export van het dossier.
- **Resultaat:** het onderscheidende kenmerk van het product werkt end-to-end.

### Fase 5 – Afronding en lancering MVP (2 weken)

- Privacyverklaring, voorwaarden, accountverwijdering en data-export.
- Back-ups met geteste restore, monitoring, foutopvolging.
- Beveiligingscheck (rate limiting, uploadvalidatie, e-mailverificatie).
- Gesloten bèta met 10–20 DIY'ers (forums, clubs, Reddit, motor-/autocommunity's).
- **Resultaat:** MVP live voor een kleine groep.

### Fase 6 – Na de MVP

- AI-ondersteunde validatie (OCR + afwijkingsdetectie).
- Onderhoudsschema's en herinneringen per e-mail.
- Uitbreiding naar motor/brommer en vrachtwagen met type-specifieke velden en schema's.
- CSV-import, PWA, publieke API.
- Verdienmodel testen.

## 10. Kwaliteit en testen

- **Tests:** pytest-django; focus op datamodel-regels, overdrachtsflow en rechten (wie mag wat zien).
- **Rechtencontrole:** schrijf expliciete tests dat gebruiker A nooit data van gebruiker B ziet. Dit is bij een dossierproduct het belangrijkste risico.
- **CI:** lint, typecheck (mypy), tests en migratiecontrole bij elke push.
- **Staging:** elke release eerst op staging, met een kopie van geanonimiseerde data.

## 11. Risico's en mitigaties

| Risico | Impact | Mitigatie |
| --- | --- | --- |
| Gebruikers vullen niets in (te veel moeite) | Hoog | Minimale verplichte velden, kenteken-autofill, snelle invoer op mobiel |
| Validatie is niet geloofwaardig | Hoog | Transparante vertrouwensniveaus, audit trail, geen overdreven claims |
| Fraude of nepbonnen | Middel | Hashchecks, afwijkingsdetectie, backoffice-controle |
| Dataverlies | Hoog | Dagelijkse back-ups, geteste restore, objectopslag met versiebeheer |
| Privacy- of AVG-problemen | Hoog | Dataminimalisatie, verwijder/export-functies, verwerkersovereenkomsten |
| Scope creep (alle voertuigtypen, fleets) | Middel | MVP = auto, rest later; strikte focus op DIY |
| Geen verdienmodel | Middel | Vroeg testen of verkopers willen betalen voor een geverifieerd dossier |
| Netwerkeffect ontbreekt | Middel | Deelbare links en PDF's als groeikanaal |

## 12. Openstaande beslissingen

1. **Licentie en verdienmodel:** open source (welke licentie) of gesloten starten?
   1. Gesloten starten voor nu
2. **Front-end:** HTMX (aanbevolen) of een SPA-framework?
   1. HTMX
3. **Authenticatie:** allauth in Django of externe provider (Keycloak/Auth0)?
   1. allauth in Django&#32;
4. **AI-validatie:** zelf gehost, EU-aanbieder of later pas?
   1. Later pas
5. **Overdracht:** krijgt de oude eigenaar een kopie, of verdwijnt zijn toegang?
   1. Kopie
6. **Landen:** alleen NL starten (RDW) of direct internationaal?
   1. Alleen NL voor nu
7. **Hosting:** Dokku op een VPS nu, managed later?
   1. Dokku op een VPS

## 13. Voorgestelde eerste stappen (komende twee weken)

1. Leg de beslissingen uit hoofdstuk 12 vast, ook als voorlopig.
2. Werk het **datamodel** uit in een ERD en bespreek dit met iemand die kritisch meekijkt.
3. Zet de repository, Docker en een Dokku-staging op.
4. Bouw inloggen via allauth en de eerste voertuigpagina.
5. Schets de schermen: voertuigoverzicht, onderhoudstijdlijn, entry toevoegen op mobiel, overdracht.
6. Praat met 5 DIY'ers over hoe ze nu bijhouden wat ze doen en wat ze kopers zouden laten zien.
