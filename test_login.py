"""
Testira konekciju i login na TVI platformu.
Pokretanje: python test_login.py
"""

import os
from dotenv import load_dotenv
from ddp_client import MeteorDDP

load_dotenv(override=True)

url      = os.getenv("METEOR_WSS_URL", "").strip()
username = os.getenv("USERNAME", "").strip()
password = os.getenv("PASSWORD", "").strip()

print(f"Server:    {url}")
print(f"Korisnik:  {username}")
print(f"Lozinka:   {'*' * len(password) if password else '(PRAZNO — dodaj u .env)'}\n")

if not password:
    print("GRESKA: Lozinka nije postavljena u .env fajlu.")
    print("Otvori .env i dodaj: PASSWORD=tvojalozinka")
    raise SystemExit(1)

print("Povezivanje...")
ddp = MeteorDDP(url)
if not ddp.connect():
    print("GRESKA: Nije moguce povezati se na server.")
    raise SystemExit(1)
print("  Konekcija OK")

print("Prijava...")
if ddp.login(username, password):
    print(f"  Login OK  —  user_id: {ddp.user_id}")
    print("\nSve radi! Mozes koristiti activity_tracker.py i submit_time.py.")
else:
    print("  GRESKA: Pogresno korisnicko ime ili lozinka.")

ddp.close()
