"""
stc_pdf.py — PDF til Obsidian-notat
=====================================
Overvaker PDF_inn/-mappa i vaulten kvart 5. sekund.
Når ein ny PDF dukkar opp:
  1. Trekk ut tekst med pdfplumber
  2. Sender til Claude for strukturering
  3. Skriv ferdig Obsidian-notat til riktig mappe
  4. Flyttar PDF til PDF_arkiv/ (så ho ikkje blir prosessert to gonger)

Mappe-struktur:
  vault/PDF_inn/       ← dropp PDF-ar her
  vault/PDF_arkiv/     ← prosesserte PDF-ar hamnar her

Bruk: python stc_pdf.py
Stopp: Ctrl+C
"""

import os, re, sys, time, shutil, anthropic, pdfplumber
from datetime import date
from pathlib import Path

os.environ.setdefault("PYTHONIOENCODING", "utf-8")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ── Finn vault ─────────────────────────────────────────────────────────────────
_parent = Path("C:/Users/Karthik/OneDrive/Obidian stasj")
_match  = [d for d in _parent.iterdir() if "stash" in d.name.lower() and "Copy" not in d.name]
if not _match:
    print("FEIL: Fann ikkje vault-mappa!"); raise SystemExit(1)

VAULT    = _match[0]
PDF_INN  = VAULT / "PDF_inn"
PDF_ARK  = VAULT / "PDF_arkiv"
MODEL    = "claude-haiku-4-5"
POLL     = 5

PDF_INN.mkdir(exist_ok=True)
PDF_ARK.mkdir(exist_ok=True)

if not os.environ.get("ANTHROPIC_API_KEY"):
    print("FEIL: ANTHROPIC_API_KEY er ikkje sett!"); raise SystemExit(1)

client = anthropic.Anthropic()

print("StC PDF-agent startar")
print(f"Overvaker: {PDF_INN}")
print("Dropp PDF-ar i PDF_inn-mappa — notat kjem automatisk")
print("Ctrl+C for aa stoppe\n")

# Les CRITICAL_FACTS
try:
    critical = (VAULT / "CRITICAL_FACTS.md").read_text(encoding="utf-8")[:400]
except Exception:
    critical = "Katchi (Karthik Senthil Ganesh), medisinstudent UiO."

# ── Vel riktig mappe basert på innhald ────────────────────────────────────────
def gjet_mappe(tekst, filnamn):
    """Enkel heuristikk for å plassere notatet i riktig mappe."""
    t = (tekst + filnamn).lower()
    if any(w in t for w in ["statistikk", "stk", "sannsyn", "fordeling", "konfidensintervall"]):
        return VAULT / "Honours og Matte" / "Semesterer" / "Semester 1" / "STK1100"
    if any(w in t for w in ["nevrologi", "neurology", "nerve", "hjerne", "aksjonspotensial"]):
        return VAULT / "Medisin" / "Nevrologi"
    if any(w in t for w in ["cellebio", "celle", "membran", "dna", "protein", "metabolisme", "glykolyse"]):
        return VAULT / "Medisin" / "Modul 1" / "Blokk 2" / "CelleBio"
    if any(w in t for w in ["histologi", "vev", "epitel"]):
        return VAULT / "Medisin" / "Modul 1" / "Blokk 2" / "Histologi"
    if any(w in t for w in ["eeg", "epic", "hjertestans", "prognose"]):
        return VAULT / "Forskning" / "EPIC AI"
    if any(w in t for w in ["matte", "lineær", "vektor", "matrise", "mat1"]):
        return VAULT / "Honours og Matte"
    return VAULT / "Medisin" / "Modul 1"

# ── Les PDF ────────────────────────────────────────────────────────────────────
def les_pdf(path):
    """Trekk ut tekst frå PDF. Returnerer tekst og sideantal."""
    tekst   = ""
    sider   = 0
    try:
        with pdfplumber.open(path) as pdf:
            sider = len(pdf.pages)
            for side in pdf.pages[:20]:  # Maks 20 sider
                side_tekst = side.extract_text()
                if side_tekst:
                    tekst += side_tekst + "\n\n"
    except Exception as e:
        return f"[Feil ved lesing: {e}]", 0
    return tekst[:8000], sider  # Maks 8000 teikn til API

# ── Konverter til Obsidian-notat ───────────────────────────────────────────────
def pdf_til_notat(pdf_path):
    print(f"  Prosesserer: {pdf_path.name}")

    tekst, sider = les_pdf(pdf_path)
    if not tekst.strip():
        print(f"  FEIL: Klarte ikkje lese tekst frå PDF")
        return

    print(f"  Lest {sider} sider, {len(tekst)} teikn")

    # Gjet mappe
    mappe = gjet_mappe(tekst, pdf_path.stem)
    mappe.mkdir(parents=True, exist_ok=True)

    prompt = f"""Du er ein Obsidian-notat-assistent for Katchi (ho/hennar), medisinstudent UiO.

IDENTITET:
{critical}

PDF-INNHALD frå "{pdf_path.stem}" ({sider} sider):
{tekst}

Lag eit strukturert Obsidian-notat på nynorsk basert på dette innhaldet.

Bruk dette formatet:
---
tags: [medisin, fagnotat]
dato: {date.today().isoformat()}
kjelde: {pdf_path.name}
---

# {pdf_path.stem}

## Hovudpoeng
[3-5 bullet points med det viktigaste]

## Nøkkelomgrep
[definer dei viktigaste omgrepa frå teksten]

## Detaljar
[utdjupa forklaring av hovudinnhaldet, strukturert med underoverskrifter]

## Koplingar
[[[wikilenker]] til relaterte notat i Obsidian, basert på innhaldet]

## Kunnskapsgap
[kva manglar / kva er uklart / kva bør utforskast vidare]

Bruk LaTeX ($...$) for matematiske formlar viss relevant.
Ver konkret og fagleg presis. Ikkje gjengi alt ordrett — syntetiser."""

    print("  Kallar API...")
    notat_innhald = ""
    with client.messages.stream(
        model=MODEL, max_tokens=1200,
        messages=[{"role": "user", "content": prompt}]
    ) as stream:
        for chunk in stream.text_stream:
            notat_innhald += chunk
            print(chunk, end="", flush=True)

    print("\n")

    # Skriv notat
    notat_path = mappe / f"{pdf_path.stem}.md"
    notat_path.write_text(notat_innhald, encoding="utf-8")
    print(f"  Notat skrive: {notat_path.relative_to(VAULT)}")

    # Flytt PDF til arkiv
    arkiv_path = PDF_ARK / pdf_path.name
    shutil.move(str(pdf_path), str(arkiv_path))
    print(f"  PDF arkivert: PDF_arkiv/{pdf_path.name}\n")

# ── Hovudløkke ─────────────────────────────────────────────────────────────────
sett_filer = set()
print(f"Aktiv. Ventar på PDF-ar i PDF_inn/...\n")

try:
    while True:
        time.sleep(POLL)
        for pdf_path in PDF_INN.glob("*.pdf"):
            if pdf_path in sett_filer:
                continue
            sett_filer.add(pdf_path)
            try:
                pdf_til_notat(pdf_path)
            except Exception as e:
                print(f"  Feil: {e}\n")
except KeyboardInterrupt:
    print("\nStoppa.")
