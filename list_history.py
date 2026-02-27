"""
Prikazuje istoriju radnog vremena po danima sa TVI platforme.

Pokretanje:
    python list_history.py
"""

import os
import sys
from datetime import datetime, date, timedelta
from dotenv import load_dotenv
from ddp_client import MeteorDDP

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

load_dotenv(override=True)


def ms_to_dt(ms: int) -> datetime:
    return datetime.fromtimestamp(ms / 1000)


def main() -> None:
    print("=" * 60)
    print("   TVI - Istorija radnog vremena")
    print("=" * 60 + "\n")

    # Izbor perioda
    today = date.today()
    first_of_month = today.replace(day=1)

    print(f"Period (Enter = ovaj mesec [{first_of_month:%d.%m.%Y} - {today:%d.%m.%Y}])")
    start_input = input("Od (DD.MM.GGGG): ").strip()
    end_input   = input("Do (DD.MM.GGGG): ").strip()

    try:
        if start_input:
            d, m, y = map(int, start_input.split("."))
            start_date = date(y, m, d)
        else:
            start_date = first_of_month

        if end_input:
            d, m, y = map(int, end_input.split("."))
            end_date = date(y, m, d)
        else:
            end_date = today
    except Exception:
        print("Nevazan format datuma.")
        return

    start_ms = int(datetime(start_date.year, start_date.month, start_date.day, 0, 0, 0).timestamp() * 1000)
    end_ms   = int(datetime(end_date.year,   end_date.month,   end_date.day,   23, 59, 59).timestamp() * 1000)

    # Povezi se i ucitaj
    print(f"\nUcitavanje {start_date:%d.%m.%Y} - {end_date:%d.%m.%Y}...")
    ddp = MeteorDDP(os.getenv("METEOR_WSS_URL"))
    if not ddp.connect():
        raise SystemExit("Greska: nije moguce povezati se.")
    if not ddp.login(os.getenv("USERNAME"), os.getenv("PASSWORD")):
        ddp.close()
        raise SystemExit("Greska: prijava nije uspela.")

    result = ddp.get_history(
        user_id=os.getenv("USER_ID"),
        user_name="Dalibor Gmitrovic",
        start_ms=start_ms,
        end_ms=end_ms,
    )
    ddp.close()

    if not result or "result" not in result or not result["result"]:
        print("Nema zapisa za izabrani period.")
        return

    records = result["result"]

    # Grupisanje po datumu
    by_day: dict[date, list] = {}
    for r in records:
        day = ms_to_dt(r["date"]["$date"]).date()
        by_day.setdefault(day, []).append(r)

    total_hours = 0.0
    total_rsd   = 0.0

    print()
    for day in sorted(by_day.keys()):
        day_records = by_day[day]
        day_hours = sum(r["hours"] for r in day_records)
        day_total = sum(r["total"] for r in day_records)
        total_hours += day_hours
        total_rsd   += day_total

        weekday = ["Pon", "Uto", "Sre", "Cet", "Pet", "Sub", "Ned"][day.weekday()]
        print(f"  {weekday} {day:%d.%m.%Y}  —  {day_hours:.2f}h  ({day_total:,.0f} RSD)")

        for r in sorted(day_records, key=lambda x: x["startTime"]["$date"]):
            start = ms_to_dt(r["startTime"]["$date"]).strftime("%H:%M")
            end   = ms_to_dt(r["endTime"]["$date"]).strftime("%H:%M")
            name  = r.get("requestName", "")[:40]
            comment = r.get("comment") or ""
            comment = comment[:35]
            print(f"      {start}-{end}  {r['hours']:.2f}h  {name}")
            if comment:
                print(f"                   # {comment}")

    print()
    print("=" * 60)
    print(f"  UKUPNO:  {total_hours:.2f}h   {total_rsd:,.0f} RSD")
    print(f"  Radnih dana: {len(by_day)}")
    print("=" * 60)


if __name__ == "__main__":
    main()
