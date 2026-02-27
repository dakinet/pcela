"""
Cita zabelezene aktivnosti i salje radno vreme na TVI platformu.

Pokretanje:
    python submit_time.py
"""

import os
import sys
import sqlite3
from datetime import datetime, date

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")
from pathlib import Path

from dotenv import load_dotenv

from ddp_client import MeteorDDP

load_dotenv(override=True)

DB_PATH = Path(__file__).parent / "activity_log.db"


# ── pomocne funkcije ──────────────────────────────────────────────────────────

def ms_to_str(ms: int) -> str:
    return datetime.fromtimestamp(ms / 1000).strftime("%H:%M")


def time_str_to_ms(s: str, base: date) -> int:
    h, m = map(int, s.strip().split(":"))
    return int(datetime(base.year, base.month, base.day, h, m).timestamp() * 1000)


def day_bounds(d: date) -> tuple[int, int]:
    start = int(datetime(d.year, d.month, d.day, 0, 0, 0).timestamp() * 1000)
    end = int(datetime(d.year, d.month, d.day, 23, 59, 59).timestamp() * 1000)
    return start, end


def load_activities(d: date) -> list[tuple]:
    if not DB_PATH.exists():
        return []
    s, e = day_bounds(d)
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute(
        "SELECT app_name, start_ms, end_ms, duration_sec FROM activities "
        "WHERE start_ms >= ? AND start_ms <= ? ORDER BY start_ms",
        (s, e),
    ).fetchall()
    conn.close()
    return rows


def summarize(rows: list[tuple]) -> dict[str, dict]:
    apps: dict[str, dict] = {}
    for app, start, end, dur in rows:
        if app not in apps:
            apps[app] = {"duration": 0, "start": start, "end": end}
        apps[app]["duration"] += dur
        apps[app]["start"] = min(apps[app]["start"], start)
        apps[app]["end"] = max(apps[app]["end"], end)
    return apps


def env(key: str) -> str:
    val = os.getenv(key, "").strip()
    if not val:
        raise SystemExit(f"Greska: nedostaje '{key}' u .env fajlu.")
    return val


# ── domeni i pretraga projekata ───────────────────────────────────────────────

DOMAINS = [
    ("14", "BZR I PPZ"),
    ("8",  "IZVODJENJE"),
    ("10", "NADZOR"),
    ("9",  "OPSTE I NERADNO"),
    ("6",  "Projektovanje"),
    ("12", "SERVIS"),
    ("13", "TEHNICKA KONTROLA PROJEKATA"),
]


def _oid_value(val) -> str:
    """Izvlaci hex string iz EJSON ObjectId ili vraca string direktno."""
    if isinstance(val, dict):
        return val.get("$value", "")
    return str(val) if val else ""


def select_project(ddp) -> tuple[str, str] | None:
    """Interaktivna pretraga projekata. Vraca (activities_id, requests_id) ili None."""
    print("\n  Domeni:")
    for i, (code, name) in enumerate(DOMAINS, 1):
        print(f"  {i}. {name}")

    choice = input("\n  Izbor domena [1-7]: ").strip()
    try:
        idx = int(choice) - 1
        if not (0 <= idx < len(DOMAINS)):
            raise ValueError
        domain_code, domain_name = DOMAINS[idx]
    except (ValueError, IndexError):
        print("  Nevazan izbor.")
        return None

    term = input(f"  Naziv (npr. *rec za pretragu) [*]: ").strip()
    if not term:
        term = "*"
    elif not term.startswith("*"):
        term = "*" + term

    print(f"  Pretrazivanje '{domain_name}' / '{term}'...")
    docs = ddp.search_activities(domain_code, term)

    if not docs:
        print("  Nema rezultata.")
        return None

    print(f"\n  Pronadjeno {len(docs)} projekata:")
    print("  " + "-" * 60)
    for i, doc in enumerate(docs, 1):
        num  = doc.get("activityNumber", "")
        name = doc.get("name", "(bez naziva)")[:50]
        print(f"  {i:2}. [{num}] {name}")
    print("  " + "-" * 60)

    pick = input(f"\n  Izbor projekta [1-{len(docs)}, 0=odustani]: ").strip()
    try:
        pick_idx = int(pick) - 1
        if pick_idx == -1:
            return None
        if not (0 <= pick_idx < len(docs)):
            raise ValueError
    except ValueError:
        print("  Nevazan izbor.")
        return None

    chosen = docs[pick_idx]
    act_id = chosen["_id"]
    req_id = _oid_value(chosen.get("requests_id", ""))

    print(f"  Izabrano: [{chosen.get('activityNumber', '')}] {chosen.get('name', '')[:50]}")
    return act_id, req_id


# ── glavni tok ────────────────────────────────────────────────────────────────

def main() -> None:
    print("=" * 44)
    print("   TVI - Unos radnog vremena")
    print("=" * 44 + "\n")

    # Ucitaj konfiguraciju
    meteor_url      = env("METEOR_WSS_URL")
    username        = env("USERNAME")
    password        = env("PASSWORD")
    user_id         = env("USER_ID")
    price_per_h     = int(env("PRICE_PER_HOUR"))
    activities_id   = env("DEFAULT_ACTIVITIES_ID")
    requests_id     = env("DEFAULT_REQUESTS_ID")

    # Izbor datuma
    today = date.today()
    day_input = input(f"Datum [{today:%d.%m.%Y}]: ").strip()
    if day_input:
        try:
            d, m, y = map(int, day_input.split("."))
            today = date(y, m, d)
        except Exception:
            print("Nevazan format, koristi se danasnji datum.")

    # Ucitaj aktivnosti
    rows = load_activities(today)

    if rows:
        apps = summarize(rows)
        first_ms = min(r[1] for r in rows)
        last_ms  = max(r[2] for r in rows)
        total_sec = sum(r[3] for r in rows)

        print(f"\nAktivnosti za {today:%d.%m.%Y}:")
        print("─" * 54)
        sorted_apps = sorted(apps.items(), key=lambda x: x[1]["duration"], reverse=True)
        for app, data in sorted_apps:
            h = data["duration"] / 3600
            print(f"  {app[:42]:42s}  {h:4.1f}h")
        print("─" * 54)
        print(f"  {'UKUPNO':42s}  {total_sec/3600:4.1f}h\n")
        print(f"  Detektovano: {ms_to_str(first_ms)} – {ms_to_str(last_ms)}")

        # Mogucnost izmene vremena
        override = input("\nZameni vreme rada? (Enter = ne, ili '08:00-16:00'): ").strip()
        if override and "-" in override:
            try:
                s_str, e_str = override.split("-", 1)
                first_ms = time_str_to_ms(s_str, today)
                last_ms  = time_str_to_ms(e_str, today)
                print(f"  Postavljeno: {ms_to_str(first_ms)} – {ms_to_str(last_ms)}")
            except Exception:
                print("  Nevazan format, zadrzava se detektovano vreme.")

        # Automatski komentar od top 5 aplikacija
        auto_comment = ", ".join(app for app, _ in sorted_apps[:5])

    else:
        print(f"\nNema zabelezenih aktivnosti za {today:%d.%m.%Y}.")
        print("Pokreni activity_tracker.py tokom radnog dana za automatsko pracenje.\n")

        manual = input("Unesi vreme rucno? (da/ne): ").strip().lower()
        if manual != "da":
            return

        s_str = input("Pocetak (HH:MM): ").strip()
        e_str = input("Kraj    (HH:MM): ").strip()
        first_ms = time_str_to_ms(s_str, today)
        last_ms  = time_str_to_ms(e_str, today)
        auto_comment = ""

    # Izracunaj sate
    hours = round((last_ms - first_ms) / 3_600_000, 4)
    total = round(hours * price_per_h)

    print(f"\n  Sati za unos: {hours:.2f}h  ({ms_to_str(first_ms)} – {ms_to_str(last_ms)})")

    # Izbor projekta
    proj_choice = input("\nProjekat [Enter = podrazumevani, 'p' = pretrazi]: ").strip().lower()
    ddp = None
    if proj_choice == "p":
        print("\nPovezivanje za pretragu...")
        ddp = MeteorDDP(meteor_url)
        if not ddp.connect():
            print("Greska: nije moguce povezati se. Koristim podrazumevani projekat.")
            ddp = None
        elif not ddp.login(username, password):
            print("Greska: prijava nije uspela. Koristim podrazumevani projekat.")
            ddp.close()
            ddp = None
        else:
            found = select_project(ddp)
            if found:
                activities_id, requests_id = found
            else:
                print("  Koristim podrazumevani projekat.")

    # Komentar
    default_comment = auto_comment or "Rad na racunaru"
    comment_input = input(f"\nKomentar [{default_comment}]: ").strip()
    comment = comment_input or default_comment

    # Prikaz i potvrda
    print(f"\n  Spreman unos:")
    print(f"  -" * 22)
    print(f"  Datum:    {today:%d.%m.%Y}")
    print(f"  Vreme:    {ms_to_str(first_ms)} - {ms_to_str(last_ms)}")
    print(f"  Sati:     {hours:.2f}h")
    print(f"  Ukupno:   {total:,} RSD")
    print(f"  Komentar: {comment[:48]}")
    print(f"  -" * 22)

    if input("\nPoslati? (da/ne): ").strip().lower() != "da":
        print("Otkazano.")
        if ddp:
            ddp.close()
        return

    # Poveži se i pošalji (ili iskoristi vec otvorenu konekciju)
    if ddp is None:
        print("\nPovezivanje na TVI platformu...")
        ddp = MeteorDDP(meteor_url)
        if not ddp.connect():
            raise SystemExit("Greska: nije moguce povezati se na server.")

        print("Prijava...")
        if not ddp.login(username, password):
            ddp.close()
            raise SystemExit("Greska: prijava nije uspela. Proveri korisnicko ime i lozinku.")
    print("Slanje radnog vremena...")
    result = ddp.add_request_time(
        hours=hours,
        price_per_hour=price_per_h,
        comment=comment,
        engaged_user_id=user_id,
        start_ms=first_ms,
        end_ms=last_ms,
        activities_id=activities_id,
        requests_id=requests_id,
    )
    ddp.close()

    if result and "result" in result:
        record_id = result["result"].get("_id", {}).get("$value", "")
        print(f"\n  Uspesno! Upisano {hours:.2f}h za {today:%d.%m.%Y}.")
        if record_id:
            print(f"  ID zapisa: {record_id}")
    elif result and "error" in result:
        print(f"\n  Greska sa servera: {result['error']}")
    else:
        print("\n  Greska: nije dobijen odgovor od servera.")


if __name__ == "__main__":
    main()
