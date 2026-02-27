import os, sys
sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from ddp_client import MeteorDDP

load_dotenv(Path(__file__).parent / ".env", override=True)

start_ms = 1771860300000  # 16:25
end_ms   = int(datetime(2026, 2, 23, 17, 29, 0).timestamp() * 1000)
hours    = round((end_ms - start_ms) / 3_600_000, 4)
price    = int(os.getenv("PRICE_PER_HOUR", "2300"))

print(f"  Start  : {datetime.fromtimestamp(start_ms/1000):%H:%M}")
print(f"  End    : {datetime.fromtimestamp(end_ms/1000):%H:%M}")
print(f"  Sati   : {hours:.4f}h")
print(f"  Total  : {round(hours * price):,} RSD")
print(f"  Komentar: Kide airsense prepiska i konverzacija za oporavak modula")
print()

ddp = MeteorDDP(os.getenv("METEOR_WSS_URL"))
if not ddp.connect():
    raise SystemExit("Greska: konekcija nije uspela.")
if not ddp.login(os.getenv("USERNAME"), os.getenv("PASSWORD")):
    ddp.close()
    raise SystemExit("Greska: login nije uspeo.")

result = ddp.add_request_time(
    hours=hours,
    price_per_hour=price,
    comment="Kide airsense prepiska i konverzacija za oporavak modula",
    engaged_user_id=os.getenv("USER_ID"),
    start_ms=start_ms,
    end_ms=end_ms,
    activities_id="6a52ff142e6b2ad83b3c558f",
    requests_id="98645f49f2646121077ce298",
)
ddp.close()

if result and "result" in result:
    rec = result["result"].get("_id", {})
    rid = rec.get("$value", rec) if isinstance(rec, dict) else rec
    print(f"  Uspesno upisano! ID: {rid}")
elif result and "error" in result:
    print(f"  Greska: {result['error']}")
else:
    print("  Greska: nema odgovora.")
