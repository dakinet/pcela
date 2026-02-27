"""
Prati aktivni prozor na Windowsu i belezi u SQLite bazu.

Pokreni na pocetku radnog dana:
    python activity_tracker.py

Zaustavi sa Ctrl+C na kraju radnog dana.
"""

import sqlite3
import time
from datetime import datetime
from pathlib import Path

import win32gui

DB_PATH = Path(__file__).parent / "activity_log.db"
POLL_INTERVAL = 5  # sekundi izmedju provera


def init_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS activities (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            app_name      TEXT NOT NULL,
            window_title  TEXT NOT NULL,
            start_ms      INTEGER NOT NULL,
            end_ms        INTEGER NOT NULL,
            duration_sec  INTEGER NOT NULL
        )
    """)
    conn.commit()
    return conn


def active_window() -> str:
    try:
        return win32gui.GetWindowText(win32gui.GetForegroundWindow()) or "Radna povrsina"
    except Exception:
        return "Nepoznato"


def app_from_title(title: str) -> str:
    """Izvlaci ime aplikacije iz naslova prozora (deo posle poslednjeg ' - ')."""
    if " - " in title:
        return title.rsplit(" - ", 1)[-1].strip()
    return title.strip() or "Nepoznato"


def save_activity(conn: sqlite3.Connection, title: str, start_ms: int, end_ms: int) -> None:
    duration = max(1, (end_ms - start_ms) // 1000)
    if duration < 5:
        return
    conn.execute(
        "INSERT INTO activities (app_name, window_title, start_ms, end_ms, duration_sec) "
        "VALUES (?, ?, ?, ?, ?)",
        (app_from_title(title), title, start_ms, end_ms, duration),
    )
    conn.commit()


def main() -> None:
    conn = init_db()
    start_time = datetime.now()
    print(f"[{start_time:%H:%M:%S}] Pracenje aktivnosti pokrenuto.")
    print("Zaustavi sa Ctrl+C kada zavrsis radni dan.\n")

    current_title = active_window()
    current_start = int(time.time() * 1000)

    try:
        while True:
            time.sleep(POLL_INTERVAL)
            now_ms = int(time.time() * 1000)
            title = active_window()

            if title != current_title:
                save_activity(conn, current_title, current_start, now_ms)
                app = app_from_title(title)
                print(f"[{datetime.now():%H:%M:%S}] {app}")
                current_title = title
                current_start = now_ms

    except KeyboardInterrupt:
        now_ms = int(time.time() * 1000)
        save_activity(conn, current_title, current_start, now_ms)
        elapsed = datetime.now() - start_time
        h, rem = divmod(int(elapsed.total_seconds()), 3600)
        m = rem // 60
        print(f"\n[{datetime.now():%H:%M:%S}] Pracenje zaustavljeno. Ukupno praceno: {h}h {m}m")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
