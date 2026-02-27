# TVI Platforma — Beleške i naučene lekcije

## Arhitektura platforme

- **URL:** https://tvi.teaminoving2.rs
- **Backend:** Meteor.js SPA
- **Protokol:** DDP (Distributed Data Protocol) preko SockJS WebSocket
- **WebSocket URL:** `wss://tvi.meteor.teaminoving2.rs`
- **SockJS URL pattern:** `wss://host/sockjs/{3-cifre}/{8-char-session}/websocket`
- **SockJS framing:** `o` = open, `h` = heartbeat, `a["json"]` = niz poruka, `c` = close

---

## Login

Platforma koristi **nestandardni** Meteor login (ne SHA-256):

```json
{"msg": "method", "method": "login", "params": [{"username": "...", "pass": "..."}]}
```

**NE** koristi standardni Meteor SHA-256 format `{"user": {...}, "password": {"digest": ..., "algorithm": "sha-256"}}`.

---

## DDP Metode

| Metoda | Opis |
|--------|------|
| `login` | Prijava sa `{username, pass}` |
| `requests.addRequestTime` | Upisuje radno vreme |
| `requests.removeRequestTime` | Briše zapis |
| `user.mapForExportRequestTimesTvi` | Istorija radnog vremena |
| `activities.searchCount` | Broj rezultata pretrage projekata |

## DDP Subscriptions

| Subscription | Opis |
|-------------|------|
| `activities_search` | Pretraga aktivnih projekata (sa paginacijom) |

### Parametri za `activities_search` — stranica N:

```json
[
  {"domainCode": "9", "name": "*dalibor"},
  {
    "pageSize": 20,
    "currentPage": 2,
    "sortOptions": [{"value": 1, "key": "name", "translate": "ui.activity.label.name"}],
    "mongoOptionsForClient": {"sort": [["name", 1]], "skip": 20, "limit": 20},
    "mongoOptionsForServer": {"sort": [["name", 1]], "skip": 20, "limit": 20}
  },
  null,
  true
]
```

- `skip = (currentPage - 1) * pageSize`
- Wildcad `*` kao `name` vraća SVE projekte u domenu (za export)
- Paginacija: iterirati stranice dok god odgovor vrati manje od `pageSize` dokumenata
- Svaka stranica dolazi kao novi `sub` + čekanje `ready` + `unsub`

---

## Domeni (domainCode) — broj projekata (stanje 23.02.2026.)

| Kod | Naziv | Projekata |
|-----|-------|----------:|
| `6`  | Projektovanje | 311 |
| `8`  | IZVODJENJE | 107 |
| `9`  | OPSTE I NERADNO | 1232 |
| `10` | NADZOR | 16 |
| `12` | SERVIS | 1107 |
| `13` | TEHNICKA KONTROLA PROJEKATA | 3 |
| `14` | BZR I PPZ | 89 |
| | **UKUPNO** | **2865** |

---

## MongoDB / EJSON format

- ObjectId na žici: `{"$type": "oid", "$value": "hexstring"}`
- Timestamp: `{"$date": milliseconds}`
- `_id` u DDP `added` porukama dolazi kao plain hex string (ne EJSON)
- Polja unutar dokumenta (npr. `requests_id`) dolaze kao EJSON `{"$type": "oid", "$value": "..."}`

---

## Pretraga projekata — važna pravila

### ⚠️ Pretraga radi po NAZIVU, ne po broju projekta!

- `*2176*` **NEĆE** naći projekat #2176
- Treba koristiti deo naziva, npr. `*Izvođење*` ili `*Dalibor*`
- Wildcard `*` se stavlja ispred teksta za pretragu (prefix-wildcard)
- Primer: za projekat "25-027-EMS podrška za Alvis-ELEKTRO" → traži `*25-027*` (radi jer je "25-027" deo naziva)
- Za dohvat SVIH projekata u domenu: `name = "*"` (samo zvezdica)

### Pretraga vraća max 20 rezultata po stranici (pageSize)

Za sve projekte koristiti paginaciju — vidi `fetch_all_projects.py`.

---

## Struktura `add_request_time` poziva

```python
ddp.call("requests.addRequestTime", [{
    "hours": 4.0,
    "pricePerHour": 2300,
    "costPerHour": None,
    "comment": "Opis rada",
    "engagedUserId": "rSFbpNT5nqkcLc3ba",
    "startTime": {"$date": start_ms},
    "endTime":   {"$date": end_ms},
    "total": 9200,
    "activities_id": {"$type": "oid", "$value": "hexid"},
    "requests_id":   {"$type": "oid", "$value": "hexid"},
}])
```

Vraća `{"result": {"_id": {"$value": "record_hex_id"}}}` pri uspehu.

### Računanje sati i iznosa

```python
hours = round((end_ms - start_ms) / 3_600_000, 4)
total = round(hours * price_per_hour, 2)
```

---

## Struktura `get_history` poziva

```python
ddp.call("user.mapForExportRequestTimesTvi", [{
    "userId": "rSFbpNT5nqkcLc3ba",
    "userName": "Dalibor Gmitrovic",
    "startDate": {"$date": start_ms},
    "endDate":   {"$date": end_ms},
}])
```

Vraća listu zapisa. Svaki zapis sadrži:

```
r["date"]["$date"]       → datum (ms)
r["startTime"]["$date"]  → početak (ms)
r["endTime"]["$date"]    → kraj (ms)
r["hours"]               → sati (float)
r["total"]               → iznos (RSD)
r["requestName"]         → naziv projekta
r["comment"]             → komentar
r["_id"]["$value"]       → hex ID zapisa (za brisanje)
```

---

## Metode u ddp_client.py

| Metoda | Parametri | Opis |
|--------|-----------|------|
| `connect(timeout)` | — | SockJS WebSocket konekcija |
| `login(username, password)` | — | Prijava, setuje `user_id` |
| `call(method, params, timeout)` | — | Generički DDP method call |
| `add_request_time(...)` | hours, price_per_hour, comment, engaged_user_id, start_ms, end_ms, activities_id, requests_id | Upisuje radno vreme |
| `remove_request_time(record_id)` | hex string | Briše zapis po ID |
| `get_history(user_id, user_name, start_ms, end_ms)` | — | Istorija radnog vremena |
| `search_activities(domain_code, name, timeout)` | — | Pretraga projekata, stranica 1, max 20 |
| `search_activities_page(domain_code, name, page, page_size, timeout)` | page počinje od 1 | Pretraga sa paginacijom |
| `close()` | — | Zatvara WebSocket |

---

## Poznati projekti / aktivnosti

### Lični projekti Dalibora u domenu 9 (OPSTE I NERADNO):

| Broj | Naziv | `_id` (activities_id) | `requests_id` |
|------|-------|----------------------|---------------|
| #2176 | Dalibor Gmitrović Opšte Izvođenje 2026 | `6a52ff142e6b2ad83b3c558f` | `98645f49f2646121077ce298` |
| #2177 | Dalibor Gmitrović Opšte Projektovanje 2026 | `b15c9937a106b1c14b3154e0` | — |
| #2178 | Dalibor Gmitrović Opšte Servis 2026 | `8b90b309b8d677cfdccdd879` | — |
| #2179 | Dalibor Gmitrović Opšte Nadzor 2026 | `e4eb14a3d10565f8904a2270` | — |
| #2180 | Dalibor Gmitrović Opšte 2026 | `35320d26e114bbf2d8bc53b2` | `98645f49f2646121077ce298` |
| #2181 | Dalibor Gmitrović Bolovanje 2026 | `08c6b5c3aa0354fec75f273a` | — |
| #2182 | Dalibor Gmitrović Godišnji Odmor 2026 | `897c66ac9cb9b8ba1453f390` | — |
| #2183 | Dalibor Gmitrović Praznik 2026 | `4939a3dfabf582dd3649ce7c` | — |
| #2184 | Dalibor Gmitrović Automobil Privatno 2026 | `4d2c86023f948cd3886229de` | — |
| #2185 | Dalibor Gmitrović Automobil Kuća-Posao 2026 | `df204c87b06a77f3f81a7fcd` | — |

> **DEFAULT_ACTIVITIES_ID** u `.env` = `35320d26e114bbf2d8bc53b2` → ovo je **#2180 Dalibor Gmitrović Opšte 2026**

### Ostali poznati projekti:

| Broj | Naziv | Domen | `_id` | `requests_id` |
|------|-------|-------|-------|---------------|
| #413 | 25-027-EMS podrška za Alvis-ELEKTRO | — | `02e6e9bf1cc318e596171745` | `4dbf7c60235ad608ae4fa810` |

> Svi projekti svih domena su preuzeti i sačuvani u `projects/projects.db` (SQLite) i `projects/projects_SVI.txt` (23.02.2026).

---

## Tehnički problemi i rešenja

### 1. Windows USERNAME env var konflikt
`os.getenv("USERNAME")` vraća Windows sistemski nalog (npr. `daliborg`) umesto vrednosti iz `.env`.
**Rešenje:** `load_dotenv(override=True)` u svim skriptama.

### 2. Unicode / cp1252 greška
Srpska slova (ć, š, ž, đ) izazivaju `UnicodeEncodeError` na Windows konzoli.
**Rešenje:** Na početku svake skripte:
```python
sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")
```

### 3. SSL upozorenje pri WebSocket konekciji
```
UserWarning: Bad certificate in Windows certificate store: not enough data
```
Bezopasno upozorenje — konekcija radi normalno. Može se sutihnuti sa `2>/dev/null`.

### 4. DDP Subscription vs Method
- **Method** (`call`) → direktan odgovor, lako za koristiti
- **Subscription** (`sub`) → server šalje `added` poruke za svaki dokument, zatim `ready`
- Subscription ne vraća podatke direktno — treba skupljati `added` poruke dok ne stigne `ready`

### 5. load_dotenv iz stdin / inline skripte
`find_dotenv()` bez argumenata pada sa `AssertionError` kada se skripta pokreće iz stdin (`python -`).
**Rešenje:** Uvek eksplicitno navesti putanju:
```python
load_dotenv(Path(__file__).parent / ".env", override=True)
```

### 6. `unsub` nema potvrdu
DDP `unsub` poruka ne dobija confirmation od servera (za razliku od `sub` koji dobija `ready`).
`removed` poruke koje server šalje nakon unsubscribe se ignorišu jer je `_sub_collecting = False`.

---

## Fajlovi projekta

| Fajl | Opis |
|------|------|
| `ddp_client.py` | Meteor DDP/SockJS klijent (konekcija, login, metode, subscription, paginacija) |
| `activity_tracker.py` | Windows tracker aktivnih prozora → SQLite |
| `submit_time.py` | Interaktivni unos radnog vremena (sa pretragom projekata) |
| `list_history.py` | Pregled istorije radnog vremena po danima |
| `fetch_all_projects.py` | Preuzima sve projekte svih domena → SQLite + TXT fajlovi |
| `test_login.py` | Test konekcije i logina |
| `activity_log.db` | SQLite baza aktivnosti (generiše tracker) |
| `projects/projects.db` | SQLite baza svih projekata svih domena (2865 zapisa) |
| `projects/projects_SVI.txt` | Svi projekti u jednom TXT fajlu |
| `projects/projects_<kod>_<naziv>.txt` | TXT po domenu |
| `.env` | Kredencijali i podešavanja |
| `.env.example` | Primer .env bez kredencijala |
| `requirements.txt` | Python zavisnosti |

### Pomoćne skripte (jednokratne, mogu se brisati):

| Fajl | Opis |
|------|------|
| `_check_today.py` | Ispisuje sve zapise za današnji dan i poslednji end_ms |
| `_submit_now.py` | Direktni unos hardkodovanog vremenskog zapisa |
