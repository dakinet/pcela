"""
Preuzima SVE projekte sa TVI platforme po svim domenima.

Kreira:
  projects/projects_<kod>_<naziv>.txt  — po jedan fajl za svaki domen
  projects/projects_SVI.txt            — svi projekti zajedno
  projects/projects.db                 — SQLite baza sa svim projektima

Pokretanje:
    python fetch_all_projects.py
"""

import os
import sys
import sqlite3
import time
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

from dotenv import load_dotenv

from ddp_client import MeteorDDP

load_dotenv(override=True)

# ── konfiguracija ─────────────────────────────────────────────────────────────

DOMAINS = [
    ("6",  "Projektovanje"),
    ("8",  "IZVODJENJE"),
    ("9",  "OPSTE_I_NERADNO"),
    ("10", "NADZOR"),
    ("12", "SERVIS"),
    ("13", "TEHNICKA_KONTROLA"),
    ("14", "BZR_I_PPZ"),
]

PAGE_SIZE  = 20
PAUSE_SEC  = 0.4   # pauza između stranica da se ne preoptereti server

OUTPUT_DIR = Path(__file__).parent / "projects"
DB_PATH    = OUTPUT_DIR / "projects.db"


# ── pomocne funkcije ──────────────────────────────────────────────────────────

def env(key: str) -> str:
    val = os.getenv(key, "").strip()
    if not val:
        raise SystemExit(f"Greska: nedostaje '{key}' u .env fajlu.")
    return val


def _oid_value(val) -> str:
    if isinstance(val, dict):
        return val.get("$value", "")
    return str(val) if val else ""


# ── SQLite ────────────────────────────────────────────────────────────────────

def init_db(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS projects (
            id              TEXT PRIMARY KEY,
            activity_number TEXT,
            name            TEXT,
            domain_code     TEXT,
            domain_name     TEXT,
            requests_id     TEXT,
            fetched_at      TEXT
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_domain ON projects(domain_code)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_number ON projects(activity_number)")
    conn.commit()


def upsert_docs(conn: sqlite3.Connection, docs: list[dict],
                domain_code: str, domain_name: str, fetched_at: str) -> None:
    rows = []
    for doc in docs:
        rows.append((
            doc["_id"],
            str(doc.get("activityNumber", "")),
            doc.get("name", ""),
            domain_code,
            domain_name,
            _oid_value(doc.get("requests_id", "")),
            fetched_at,
        ))
    conn.executemany(
        "INSERT OR REPLACE INTO projects "
        "(id, activity_number, name, domain_code, domain_name, requests_id, fetched_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        rows,
    )
    conn.commit()


# ── dohvatanje sa servera ─────────────────────────────────────────────────────

def fetch_domain(ddp: MeteorDDP, domain_code: str, domain_name: str) -> list[dict]:
    """Prolazi sve stranice za jedan domen i vraca sve projekte."""
    all_docs: list[dict] = []
    page = 1

    while True:
        print(f"    str. {page:3d} ... ", end="", flush=True)
        docs = ddp.search_activities_page(domain_code, "*", page=page, page_size=PAGE_SIZE)
        print(f"{len(docs):3d} projekata")

        all_docs.extend(docs)

        if len(docs) < PAGE_SIZE:
            # Poslednja stranica — kraj
            break

        page += 1
        time.sleep(PAUSE_SEC)

    return all_docs


# ── pisanje txt fajlova ───────────────────────────────────────────────────────

def write_domain_txt(docs: list[dict], domain_code: str, domain_name: str,
                     path: Path, fetched_at: str) -> None:
    sorted_docs = sorted(docs, key=lambda d: str(d.get("activityNumber", "")).zfill(10))
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"# Domen [{domain_code}]: {domain_name}\n")
        f.write(f"# Preuzeto: {fetched_at}\n")
        f.write(f"# Ukupno projekata: {len(docs)}\n")
        f.write("=" * 80 + "\n\n")

        for doc in sorted_docs:
            num     = doc.get("activityNumber", "")
            name    = doc.get("name", "(bez naziva)")
            doc_id  = doc["_id"]
            req_id  = _oid_value(doc.get("requests_id", ""))

            f.write(f"[{num}] {name}\n")
            f.write(f"       activities_id : {doc_id}\n")
            if req_id:
                f.write(f"       requests_id   : {req_id}\n")
            f.write("\n")


def write_combined_txt(conn: sqlite3.Connection, path: Path, fetched_at: str) -> None:
    total = conn.execute("SELECT COUNT(*) FROM projects").fetchone()[0]

    with open(path, "w", encoding="utf-8") as f:
        f.write("# SVI PROJEKTI — TVI platforma\n")
        f.write(f"# Preuzeto: {fetched_at}\n")
        f.write(f"# Ukupno projekata: {total}\n")
        f.write("=" * 80 + "\n")

        cur_domain = None
        rows = conn.execute(
            "SELECT domain_code, domain_name, activity_number, name, id, requests_id "
            "FROM projects ORDER BY domain_code+0, CAST(activity_number AS INTEGER)"
        ).fetchall()

        for dc, dn, num, name, doc_id, req_id in rows:
            if dc != cur_domain:
                cur_domain = dc
                f.write(f"\n\n## Domen [{dc}]: {dn}\n")
                f.write("-" * 60 + "\n\n")

            f.write(f"[{num}] {name}\n")
            f.write(f"       activities_id : {doc_id}\n")
            if req_id:
                f.write(f"       requests_id   : {req_id}\n")
            f.write("\n")


# ── main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    print("=" * 60)
    print("  TVI — Preuzimanje svih projekata")
    print("=" * 60 + "\n")

    meteor_url = env("METEOR_WSS_URL")
    username   = env("USERNAME")
    password   = env("PASSWORD")

    OUTPUT_DIR.mkdir(exist_ok=True)

    # Konekcija
    print("Povezivanje na TVI platformu...")
    ddp = MeteorDDP(meteor_url)
    if not ddp.connect():
        raise SystemExit("Greska: nije moguce povezati se.")

    print("Prijava...")
    if not ddp.login(username, password):
        ddp.close()
        raise SystemExit("Greska: prijava nije uspela.")

    print("OK\n")

    fetched_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = sqlite3.connect(DB_PATH)
    init_db(conn)

    totals: dict[str, int] = {}

    for domain_code, domain_name in DOMAINS:
        print(f"\n[{domain_code:>2}] {domain_name}")
        print("  " + "-" * 40)

        docs = fetch_domain(ddp, domain_code, domain_name)
        totals[domain_name] = len(docs)
        print(f"  → Ukupno: {len(docs)} projekata")

        # SQLite
        upsert_docs(conn, docs, domain_code, domain_name, fetched_at)

        # TXT po domenu
        txt_name = f"projects_{domain_code}_{domain_name}.txt"
        txt_path = OUTPUT_DIR / txt_name
        write_domain_txt(docs, domain_code, domain_name, txt_path, fetched_at)
        print(f"  → {txt_name}")

        time.sleep(PAUSE_SEC)

    # Kombinovani TXT
    combined = OUTPUT_DIR / "projects_SVI.txt"
    write_combined_txt(conn, combined, fetched_at)
    print(f"\n  → {combined.name}")

    ddp.close()
    conn.close()

    # Rezime
    grand_total = sum(totals.values())
    print(f"\n{'=' * 60}")
    print(f"  Gotovo!  Preuzeto {grand_total} projekata ukupno")
    print(f"  Izlazni direktorij: {OUTPUT_DIR}")
    print(f"  Baza podataka:      projects.db")
    print()
    for name, count in totals.items():
        print(f"    {name:<30s} {count:4d}")
    print("=" * 60)


if __name__ == "__main__":
    main()
