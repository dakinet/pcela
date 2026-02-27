# Pčela — Tok komunikacije: AI upis radnog vremena

## Scenario: "Upiši mi 8-16h na projektu Opšte Servis"

---

### 1. Korisnik piše poruku → Browser

Tekst ide na `POST /api/chat` kao JSON sa celom istorijom razgovora:

```json
{
  "messages": [
    {"role": "user", "content": "Upiši od 8 do 16h na projektu opšte servis..."}
  ]
}
```

---

### 2. Backend gradi kontekst → `api.py`

Pre nego što pozove AI, backend:
- **Loguje se na TVI** (Meteor DDP WebSocket) sa tvojim kredencijalima
- **Povlači današnje unose** iz TVI
- **Gradi system prompt** koji sadrži: tvoje ime, ko si, šta si već radio danas,
  koliko ukupno sati, ostatak meseca — sve to AI dobija kao "pozadinski kontekst"

---

### 3. Poziv Gemini AI → Google API

Backend šalje HTTP POST na Google Gemini API:

```
system_prompt: "Ti si Pčela, AI asistent za TVI evidenciju...
                Danas: Dalibor Gmitrović
                Upisano: 08:00–10:30 (2:30h) Opšte Servis..."

messages: [user: "Upiši od 8 do 16h..."]
```

---

### 4. AI prepoznaje nameru → traži pretragu

Gemini analizira poruku i shvata da treba naći projekat. Vraća tekst sa **action tagom**:

```
⚙{"tool":"tvi_search","pojam":"Dalibor opšte servis"}⚙
```

Backend **parsira taj tag** (`_parse_action_tag()`) — ovo nije standardni function
calling, nego dogovoreni format teksta (zbog PROHIBITED_CONTENT blokade Gemini
function calling API-ja).

---

### 5. Pretraga projekata → SQLite lokalno

Backend poziva `_chat_search_projects("Dalibor opšte servis")`:
- Učita sve ~3000 projekata iz **lokalne SQLite baze** (`projects/projects.db`)
- Normalizuje Unicode (š→s, ć→c...) da bi našao i ćirilična/latinična imena
- Filtrira projekte koji sadrže SVE reči iz upita
- Vraća formatirane rezultate:

```
project_number=2178 → Dalibor Gmitrović Opšte Servis 2026
project_number=2180 → Dalibor Gmitrović Opšte 2026
⚠ KRITIČNO: prepiši cifru doslovno...
```

---

### 6. Drugi poziv Gemini → sa rezultatima pretrage

Backend ubacuje rezultate i ponovo zove Gemini (multi-round petlja, max 3 runde):

```
[Rezultat tvi_search]
project_number=2178 → Dalibor Gmitrović Opšte Servis 2026
...
OBAVEZNO navedi project_number=XXXX u svom odgovoru korisniku.
```

AI odgovara korisniku vidljivom porukom:

> "Pronašla sam Dalibor Gmitrović Opšte Servis 2026 (project_number=2178).
>  Planiram upis 08:00–16:00. Da li je to u redu?"

---

### 7. Korisnik potvrđuje → novi HTTP request

Korisnik piše "Da". Browser šalje **novi** `POST /api/chat` sa celom istorijom
uključujući AI-jevu prethodnu poruku (koja sada sadrži `project_number=2178`).

Gemini vidi u historiji "project_number=2178" i vraća:

```
⚙{"tool":"tvi_log","start_time":"08:00","end_time":"16:00","project_number":"2178","comment":"..."}⚙
```

---

### 8. Upis na TVI → Meteor DDP WebSocket

Backend poziva `tvi_log` MCP alat koji:
1. Pronalazi u SQLite: `2178 → activities_id` (MongoDB ObjectId)
2. Otvara **WebSocket konekciju** na `wss://tvi.meteor.teaminoving2.rs`
3. Šalje DDP `method` poruku `requests.addRequestTime` sa:
   - startTime, endTime (Unix timestamp u ms)
   - activities_id, requests_id (MongoDB OID-ovi)
   - engagedUserId, hours, pricePerHour, total
4. Čeka potvrdu od TVI servera

---

### 9. Odgovor korisniku

Backend vraća AI poruku sa rezultatom:

> "Upisano: 08:00–16:00 (8:00h) Dalibor Gmitrović Opšte Servis 2026 ✓"

---

## Dijagram toka

```
Browser
  │ POST /api/chat
  ▼
api.py (FastAPI)
  ├─→ TVI WebSocket       → povuci today's records (kontekst)
  ├─→ Google Gemini API   → "traži projekat" → action tag tvi_search
  ├─→ SQLite projects.db  → pretraga lokalno (bez interneta)
  ├─→ Google Gemini API   → "potvrdi plan" → vidljiva poruka korisniku
  │     ↑ korisnik kaže "Da" (novi HTTP request)
  ├─→ Google Gemini API   → action tag tvi_log
  └─→ TVI WebSocket       → requests.addRequestTime
  │ JSON odgovor
  ▼
Browser (prikazuje rezultat)
```

---

## Tehnologije

| Sloj | Tehnologija |
|------|-------------|
| Web server | FastAPI (Python) + Uvicorn |
| AI model | Google Gemini 2.5 Flash |
| TVI protokol | Meteor DDP over SockJS WebSocket |
| Lokalna baza | SQLite (projekti, automobili, kilometraža) |
| Frontend | Vanilla HTML/CSS/JavaScript (SPA) |
| Glasovni unos | Web Speech API (browser-native) |
| Javni pristup | Cloudflare Tunnel |
| Deploy | GitHub Actions → self-hosted runner na LAN serveru |

---

## Napomene o dizajnu

- **Zašto lokalna SQLite umesto direktne pretrage na TVI?**
  TVI nema REST API za pretragu — sve ide kroz Meteor DDP WebSocket subscription
  koji je spor (~3–10s po pozivu). SQLite sync se radi jednom noću u 04:00.

- **Zašto text tagovi umesto Gemini function calling?**
  Gemini function calling API vraća `PROHIBITED_CONTENT` za alate koji rade sa
  radnim vremenom (verovatno false positive moderacije). Text tag `⚙{...}⚙`
  zaobilazi tu blokadu.

- **Zašto project_number mora biti u vidljivoj poruci?**
  Chat je stateless — svaki "Da/Ne" korisnika je novi HTTP request bez pristupa
  prethodnim backend injection porukama. Jedino što preživljava između poziva je
  vidljivi tekst u chat historiji.
