import os, sys
sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")
from datetime import datetime, date
from pathlib import Path
from dotenv import load_dotenv
from ddp_client import MeteorDDP

load_dotenv(Path(__file__).parent / ".env", override=True)

today = date.today()
start_ms = int(datetime(today.year, today.month, today.day, 0, 0, 0).timestamp() * 1000)
end_ms   = int(datetime(today.year, today.month, today.day, 23, 59, 59).timestamp() * 1000)

ddp = MeteorDDP(os.getenv("METEOR_WSS_URL"))
ddp.connect()
ddp.login(os.getenv("USERNAME"), os.getenv("PASSWORD"))

result = ddp.get_history(
    user_id=os.getenv("USER_ID"),
    user_name="Dalibor Gmitrovic",
    start_ms=start_ms,
    end_ms=end_ms,
)
ddp.close()

if not result or "result" not in result or not result["result"]:
    print("NEMA_ZAPISA")
else:
    records = result["result"]
    for r in sorted(records, key=lambda x: x["startTime"]["$date"]):
        s = datetime.fromtimestamp(r["startTime"]["$date"]/1000).strftime("%H:%M")
        e = datetime.fromtimestamp(r["endTime"]["$date"]/1000).strftime("%H:%M")
        name = r.get("requestName","")[:55]
        print(f"  {s}-{e}  {r['hours']:.2f}h  {name}")
    last_end_ms = max(r["endTime"]["$date"] for r in records)
    last_end = datetime.fromtimestamp(last_end_ms/1000).strftime("%H:%M")
    print(f"LAST_END={last_end}")
    print(f"LAST_END_MS={last_end_ms}")
