"""
ciel_doctor.py — Helsesjekk for Ciel-hjernen
=============================================
Køyr denne når du lurer på om Ciel "berre fungerer". Han testar heile hjernen
ende-til-ende — slik tabletten ville gjort det — og gir ein tydeleg ✅/❌-rapport.

Sjekkar, i rekkjefølgje:
  1. ANTHROPIC_API_KEY er sett (miljøvariabel)
  2. Serveren svarar på /health
  3. Vault er funne (GET /)
  4. Eit EKTE Claude-svar kjem gjennom /api/ask (med tid)
  5. Modus-state svarar (/api/state)

Køyr:  python ciel_doctor.py
       (serveren må køyre — start med: python ciel_server.py)

Ingen hemmelegheiter vert skrivne ut. Testar berre at ting lever.
"""

import os
import sys
import time

try:
    import requests
except ImportError:
    print("FEIL: 'requests' manglar. Køyr:  pip install requests")
    raise SystemExit(1)

PORT = os.environ.get("CIEL_PORT", "8765")
BASE = f"http://127.0.0.1:{PORT}"

OK   = "✅"   # ✅
FAIL = "❌"   # ❌
WARN = "⚠️"  # ⚠️

results: list[tuple[bool, str]] = []


def check(ok: bool, label: str, detail: str = ""):
    mark = OK if ok else FAIL
    line = f"{mark}  {label}"
    if detail:
        line += f"  —  {detail}"
    print(line)
    results.append((ok, label))
    return ok


print(f"\nCiel-doktor — testar hjernen på {BASE}\n" + "-" * 48)

# 1. API-nøkkel (lokalt miljø — same prosess som serveren ville arve)
key_local = bool(os.environ.get("ANTHROPIC_API_KEY"))
check(key_local, "ANTHROPIC_API_KEY i dette skalet",
      "sett" if key_local else "IKKJE sett — last inn med: "
      "$env:ANTHROPIC_API_KEY = [Environment]::GetEnvironmentVariable('ANTHROPIC_API_KEY','User')")

# 2. Server oppe?
server_up = False
try:
    r = requests.get(f"{BASE}/health", timeout=5)
    server_up = r.status_code == 200 and r.json().get("ok") is True
    check(server_up, "Server svarar på /health", r.json().get("ts", ""))
except Exception as e:
    check(False, "Server svarar på /health",
          f"når ikkje {BASE} — køyr 'python ciel_server.py' først ({type(e).__name__})")

if not server_up:
    print("-" * 48)
    print(f"\n{FAIL}  Hjernen køyrer ikkje. Start serveren og prøv igjen.\n")
    raise SystemExit(1)

# 3. Vault funne + nøkkel sett SERVER-side (GET /)
try:
    info = requests.get(f"{BASE}/", timeout=5).json()
    check(bool(info.get("vault")), "Vault funne", info.get("vault", "?"))
    check(bool(info.get("key_set")), "API-nøkkel sett i server-prosessen",
          "ja" if info.get("key_set") else "nei — serveren starta utan nøkkel")
    models = info.get("models", {})
    print(f"     Modellar: vanleg={models.get('simple')} · djup={models.get('complex')}")
except Exception as e:
    check(False, "Vault/info (GET /)", f"{type(e).__name__}: {e}")

# 4. Ekte Claude-svar gjennom pipelinen
try:
    t0 = time.time()
    r = requests.post(f"{BASE}/api/ask",
                      json={"question": "Svar berre med ordet OK.", "deep": False},
                      timeout=60)
    dt = time.time() - t0
    ans = (r.json().get("answer") or "").strip()
    got = r.status_code == 200 and len(ans) > 0
    check(got, "Ekte Claude-svar via /api/ask",
          f"{dt:.1f}s · modell={r.json().get('model')} · svar: «{ans[:40]}»")
except Exception as e:
    check(False, "Ekte Claude-svar via /api/ask", f"{type(e).__name__}: {e}")

# 5. Modus-state
try:
    st = requests.get(f"{BASE}/api/state", timeout=5).json()
    check(bool(st.get("mode")), "Modus-state (/api/state)",
          f"{st.get('mode')} · {st.get('colour')}")
except Exception as e:
    check(False, "Modus-state (/api/state)", f"{type(e).__name__}: {e}")

# Oppsummering
print("-" * 48)
passed = sum(1 for ok, _ in results if ok)
total  = len(results)
if passed == total:
    print(f"\n{OK}  Alt friskt — {passed}/{total}. Ciel-hjernen er klar.\n")
    raise SystemExit(0)
else:
    feil = [label for ok, label in results if not ok]
    print(f"\n{WARN}  {passed}/{total} OK. Sjekk: {', '.join(feil)}\n")
    raise SystemExit(1)
