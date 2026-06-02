"""
stc_morning.py — Dagleg morgenbriefing til Obsidian
====================================================
Genererer _DAGLEG.md med:
  - Kva du har jobba med siste veka
  - Kva du har gløymt (ikkje opna på 30+ dagar)
  - Kunnskapsgap mot pensum
  - Kva som skjer i dag / kommande deadlines
  - Forslag til kva du bør studere i dag

Bruk (manuelt):
    python stc_morning.py

Automatisk kvar morgon — legg til i Windows Task Scheduler:
    Trigger: Dagleg kl. 07:30
    Action:  python C:\\Users\\Karthik\\.claude\\stc_morning.py
"""

import os, re, sys, time, anthropic
from datetime import date, datetime, timedelta
from pathlib import Path

os.environ.setdefault("PYTHONIOENCODING", "utf-8")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ── Finn vault ─────────────────────────────────────────────────────────────────
_parent = Path("C:/Users/Karthik/OneDrive/Obidian stasj")
_match  = [d for d in _parent.iterdir() if "stash" in d.name.lower() and "Copy" not in d.name]
if not _match:
    print("FEIL: Fann ikkje vault-mappa!"); raise SystemExit(1)

VAULT  = _match[0]
DAGLEG = VAULT / "_DAGLEG.md"
MODEL  = "claude-haiku-4-5"
IGNORE = {".obsidian", ".trash", "Usikkere notat ord"}

if not os.environ.get("ANTHROPIC_API_KEY"):
    print("FEIL: ANTHROPIC_API_KEY er ikkje sett!"); raise SystemExit(1)

client = anthropic.Anthropic()
today  = date.today()

print(f"Genererer morgenbriefing for {today}...")

# ── Analyser vault ─────────────────────────────────────────────────────────────
now        = datetime.now().timestamp()
veke_sidan = now - 7  * 24 * 3600
maaned_sidan = now - 30 * 24 * 3600

siste_veka   = []   # Notat endra siste 7 dagar
gløymde      = []   # Notat ikkje rørt på 30+ dagar
alle_notat   = []

for path in VAULT.rglob("*.md"):
    if any(d in path.parts for d in IGNORE): continue
    if path.name.startswith("_"): continue
    try:
        mtime = path.stat().st_mtime
        size  = path.stat().st_size
    except Exception:
        continue

    alle_notat.append(path)

    if mtime > veke_sidan:
        siste_veka.append((mtime, path))
    elif mtime < maaned_sidan and size > 200:
        gløymde.append((mtime, path))

siste_veka.sort(reverse=True)
gløymde.sort()  # Eldst fyrst

# Les innhald frå dei siste notatane (kort utdrag)
def les_utdrag(path, maks=300):
    try:
        return path.read_text(encoding="utf-8", errors="ignore")[:maks].strip()
    except Exception:
        return ""

siste_ctx = "\n\n".join(
    f"### {p.stem} (endra {datetime.fromtimestamp(m).strftime('%d.%m')})\n{les_utdrag(p)}"
    for m, p in siste_veka[:8]
) or "Ingen notat endra siste veka."

gløymde_lista = "\n".join(
    f"- {p.stem} (sist endra {datetime.fromtimestamp(m).strftime('%d.%m.%Y')})"
    for m, p in gløymde[:10]
) or "Ingen gløymde notat."

# Les CRITICAL_FACTS for kontekst
try:
    critical = (VAULT / "CRITICAL_FACTS.md").read_text(encoding="utf-8")[:600]
except Exception:
    critical = "Katchi (Karthik Senthil Ganesh), medisinstudent UiO."

# Les dagens dagleg-notat viss det finst
dagleg_notat = ""
try:
    dagleg_path = VAULT / "Dagleg" / f"{today}.md"
    if dagleg_path.exists():
        dagleg_notat = dagleg_path.read_text(encoding="utf-8")[:400]
except Exception:
    pass

print(f"  Analysert: {len(alle_notat)} notat totalt")
print(f"  Siste veka: {len(siste_veka)} aktive notat")
print(f"  Gløymde: {len(gløymde)} notat ikkje rørt på 30+ dagar")
print("  Kallar API...")

# ── Generer briefing ───────────────────────────────────────────────────────────
prompt = f"""Du er den personlege morgon-assistenten til Katchi (ho/hennar), {today.strftime('%A %d. %B %Y')}.

IDENTITET:
{critical}

AKTIVE NOTAT SISTE VEKA:
{siste_ctx}

NOTAT IKKJE RØRT PÅ 30+ DAGAR (risiko for å gløyme):
{gløymde_lista}

DAGLEG NOTAT I DAG (om det finst):
{dagleg_notat or "Ingenting skrive enno i dag."}

STATISTIKK:
- Totalt {len(alle_notat)} notat i vaulten
- {len(siste_veka)} notat aktive siste veka
- {len(gløymde)} notat risikerer å bli gløymde

Lag ein motiverande og konkret morgonbriefing på nynorsk. Inkluder:

## Kva du jobba med siste veka
[kort oppsummering av aktive tema]

## Fare for å gløyme
[dei 3 viktigaste notatane å repetere — vel basert på medisinsk/akademisk relevans]

## Forslag til i dag
[3 konkrete ting å gjere, rangert etter prioritet]

## Vault-statistikk
[ein linje med tal]

Ver direkte, varm og motiverande. Maks 300 ord totalt."""

# Stream til terminal + samle tekst
full_text = ""
with client.messages.stream(
    model=MODEL, max_tokens=700,
    messages=[{"role": "user", "content": prompt}]
) as stream:
    for chunk in stream.text_stream:
        full_text += chunk
        print(chunk, end="", flush=True)

print("\n")

# ── Skriv til _DAGLEG.md ───────────────────────────────────────────────────────
dagleg_innhald = f"""# Dagleg briefing — {today.strftime('%A %d. %B %Y')}

*Generert automatisk av StC-agenten kl. {datetime.now().strftime('%H:%M')}*

---

{full_text.strip()}

---

*[Skriv dagens notat nedanfor]*

"""

DAGLEG.write_text(dagleg_innhald, encoding="utf-8")
print(f"Skrive til {DAGLEG.name}")
print("Opne _DAGLEG.md i Obsidian!")
