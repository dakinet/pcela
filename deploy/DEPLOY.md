# TVI Pčela — uputstvo za deploy

## Infrastruktura

| Komponenta | Lokacija |
|---|---|
| Server | 192.168.0.247 (LXC, Debian 12) |
| App direktorijum | `/opt/tvi-bee/` |
| Systemd servis | `tvi-bee` |
| Port | 7000 (interno), HTTPS na pcela.tvi.rs |
| Git repozitorijum | https://github.com/dakinet/pcela |

---

## Tipičan deploy (izmena koda)

### 1. Izmeni kod lokalno

Radi u `C:\Users\Demo room\claude\bee\`.

### 2. Pošalji na server

Iz root direktorijuma projekta pokreni:

```
powershell -ExecutionPolicy Bypass -File deploy\deploy.ps1
```

Skripta:
- kopira `api.py`, `accounts.csv`, `webapp.html` (i `Pcela.apk` ako postoji)
- restartuje `tvi-bee` servis
- ispisuje `active` ako je sve uredu

### 3. Commit i push na git

```
git add api.py webapp.html         ← konkretni fajlovi, NE git add .
git commit -m "Kratak opis izmene"
git push
```

---

## Važno — šta NE ide na git

Ovi fajlovi su u `.gitignore` jer sadrže lozinke:

- `accounts.csv` — korisnička imena i lozinke zaposlenih
- `.env` — API ključevi i podešavanja
- `deploy/.env` — SSH kredencijali servera

---

## Kredencijali servera

Čuvaju se u `deploy/.env`:

```
SERVER_IP=192.168.0.247
SERVER_USER=root
SERVER_PASS=Neznam123#
```

SSH pristup radi isključivo kroz PuTTY (`pscp` i `plink`).
PuTTY mora biti instaliran na `C:\Program Files\PuTTY\`.

---

## Ručni SSH pristup

```
plink -pw Neznam123# root@192.168.0.247
```

Korisni SSH komande:

```bash
systemctl status tvi-bee       # status servisa
systemctl restart tvi-bee      # restart
journalctl -u tvi-bee -n 50    # poslednjih 50 linija loga
ls /opt/tvi-bee/               # sadržaj app direktorijuma
```

---

## Deploy APK (Android aplikacija)

1. Otvori projekat u Android Studio (`android-app/`)
2. Build → Generate Signed APK (ili debug APK za testiranje)
3. Kopiraj APK u root direktorijum projekta kao `Pcela.apk`
4. Pokreni `deploy\deploy.ps1` — APK se automatski kopira na server

APK je dostupan na: `https://pcela.tvi.rs/Pcela.apk`

---

## Setup novog servera (jednokratno)

Ako treba postaviti na svež Debian 12:

```bash
# Na serveru (kao root):
bash /tmp/setup.sh
```

Pre toga kopirati `setup.sh` i `tvi-bee.service` na server:

```
pscp -pw Neznam123# deploy\setup.sh deploy\tvi-bee.service root@192.168.0.247:/tmp/
plink -pw Neznam123# root@192.168.0.247 bash /tmp/setup.sh
```

Nakon setup-a, pokreni normalni deploy (`deploy.ps1`).
