"""
stc_lyd.py — Lydopptak til Obsidian-notat
==========================================
Overvaker Lyd_inn/-mappa i vaulten kvart 5. sekund.
Når ein ny lydfil dukkar opp:
  1. Transkriberer med NB-Whisper (norsk-spesifikk, Nasjonalbiblioteket)
  2. Sender transkripsjon til Claude for strukturering
  3. Skriv ferdig Obsidian-notat til riktig mappe
  4. Flyttar lydfila til Lyd_arkiv/

Støttar: .mp3 .wav .m4a .ogg .webm .mp4 .flac .aac

NB-Whisper-modellar (set MODEL_WHISPER nedanfor):
  nb-whisper-tiny   → rask, OK norsk
  nb-whisper-small  → bra norsk (~480 MB)
  nb-whisper-medium → anbefalt, svært god norsk (~1.5 GB)
  nb-whisper-large  → best kvalitet (~3 GB)

Bruk: python stc_lyd.py
Stopp: Ctrl+C
"""

import os, re, sys, time, shutil, anthropic
import torch
from datetime import date
from pathlib import Path

os.environ.setdefault("PYTHONIOENCODING", "utf-8")
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")   # PyTorch/OpenMP-fix Windows
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Legg til ffmpeg i PATH viss ikkje allereie der
_ffmpeg_winget = Path("C:/Users/Karthik/AppData/Local/Microsoft/WinGet/Packages")
for _d in _ffmpeg_winget.glob("Gyan.FFmpeg*/ffmpeg-*/bin"):
    if _d.is_dir():
        os.environ["PATH"] = str(_d) + os.pathsep + os.environ.get("PATH", "")
        break

# ── Finn vault ─────────────────────────────────────────────────────────────────
_parent = Path("C:/Users/Karthik/OneDrive/Obidian stasj")
_match  = [d for d in _parent.iterdir()
           if "stash" in d.name.lower() and "Copy" not in d.name]
if not _match:
    print("FEIL: Fann ikkje vault-mappa!"); raise SystemExit(1)

VAULT         = _match[0]
LYD_INN       = VAULT / "AI" / "Lyd" / "Lyd_inn"
LYD_ARK       = VAULT / "AI" / "Lyd" / "Lyd_arkiv"
MODEL         = "claude-haiku-4-5"
MODEL_WHISPER = "NbAiLab/nb-whisper-medium"   # norsk-spesifikk modell frå Nasjonalbiblioteket
POLL          = 5
LYDFORMAT     = {".mp3", ".wav", ".m4a", ".ogg", ".webm",
                 ".mp4", ".flac", ".aac", ".opus"}

LYD_INN.mkdir(exist_ok=True)
LYD_ARK.mkdir(exist_ok=True)

if not os.environ.get("ANTHROPIC_API_KEY"):
    print("FEIL: ANTHROPIC_API_KEY er ikkje sett!"); raise SystemExit(1)

# ── Last NB-Whisper ────────────────────────────────────────────────────────────
print(f"Lastar NB-Whisper '{MODEL_WHISPER}' (kan ta litt tid fyrste gong, ~1.5 GB)...")
try:
    from transformers import pipeline as hf_pipeline
    whisper_pipe = hf_pipeline(
        "automatic-speech-recognition",
        model=MODEL_WHISPER,
        device="cpu",
        torch_dtype=torch.float32,
    )
    print(f"NB-Whisper klar — norsk-optimalisert.\n")
except ImportError:
    print("FEIL: transformers ikkje installert.")
    print("  Køyr: pip install transformers accelerate")
    raise SystemExit(1)
except Exception as e:
    print(f"FEIL ved lasting av NB-Whisper: {e}"); raise SystemExit(1)

client = anthropic.Anthropic()

print("Ciel Lyd-agent startar")
print(f"Vault     : {VAULT.name}")
print(f"Overvaker : {LYD_INN}")
print(f"Whisper   : {MODEL_WHISPER}")
print("Dropp lydfiler i Lyd_inn/ — notat kjem automatisk")
print("Ctrl+C for aa stoppe\n")

# ── Kontekst ───────────────────────────────────────────────────────────────────
try:
    critical = (VAULT / "CRITICAL_FACTS.md").read_text(encoding="utf-8")[:400]
except Exception:
    critical = "Katchi (Karthik Senthil Ganesh), medisinstudent UiO."

# ── Vel riktig vault-mappe ────────────────────────────────────────────────────
# Faktisk mappestruktur (sjekka 2026-05-25):
# VAULT/Studie/Medisin/Medisin Forelesninger/   ← standard-destinasjon
# VAULT/Studie/Medisin/Modul 1/Blokk 2/CelleBio
# VAULT/Studie/Medisin/Modul 1/Blokk 2/LSB
# VAULT/Studie/Medisin/Nevrologi/
# VAULT/Studie/Honours og Matte/
# VAULT/Studie/Honours og Matte/Semesterer/
_STUDIE  = VAULT / "Studie"
_MEDISIN = _STUDIE / "Medisin"

def gjet_mappe(tekst: str, filnamn: str) -> Path:
    t = (tekst + filnamn).lower()
    if any(w in t for w in ["statistikk", "stk", "sannsyn", "fordeling",
                             "konfidensintervall", "normalfordeling"]):
        return _STUDIE / "Honours og Matte" / "Semesterer"
    if any(w in t for w in ["nevrologi", "neurology", "nerve", "hjerne",
                             "aksjonspotensial", "synapse"]):
        return _MEDISIN / "Nevrologi"
    if any(w in t for w in ["celle", "membran", "dna", "protein",
                             "metabolisme", "glykolyse", "mitokondrie"]):
        return _MEDISIN / "Modul 1" / "Blokk 2" / "CelleBio"
    if any(w in t for w in ["histologi", "vev", "epitel", "biopsi"]):
        return _MEDISIN / "Modul 1" / "Blokk 2"
    if any(w in t for w in ["lsb", "seminargruppe", "gruppeundervisning"]):
        return _MEDISIN / "Modul 1" / "Blokk 2" / "LSB"
    if any(w in t for w in ["matte", "lineær", "vektor", "matrise", "mat1",
                             "kalkulus", "derivasjon", "integrasjon"]):
        return _STUDIE / "Honours og Matte"
    if any(w in t for w in ["anatomi", "fysiologi", "biokjemi", "farmakologi",
                             "patologi", "immunologi"]):
        return _MEDISIN / "Modul 1"
    return _MEDISIN / "Medisin Forelesninger"


# ── Transkribering ─────────────────────────────────────────────────────────────
def transkriber(lyd_path: Path) -> tuple[str, str]:
    """
    Returnerer (transkripsjon, språk).
    Bruker NB-Whisper — norsk-spesifikk modell frå Nasjonalbiblioteket.
    Handterer lange opptak automatisk via chunking (30s bitar).
    """
    print(f"  Transkriberer med NB-Whisper (norsk-optimalisert)...")
    print(f"  (rekn ca. {_estimert_tid(lyd_path)} — hent deg ein kaffi ☕)")

    start = time.time()
    result = whisper_pipe(
        str(lyd_path),
        chunk_length_s=30,      # del opp i 30-sekunders bitar → handterer 2+ timar
        batch_size=4,           # prosesser 4 bitar samstundes (CPU-venleg)
        return_timestamps=False,
        generate_kwargs={"language": "no", "task": "transcribe"},
    )
    elapsed = int(time.time() - start)
    tekst   = result["text"].strip()

    print(f"  Transkripsjon ferdig: {elapsed}s · {len(tekst.split())} ord · norsk")
    return tekst, "no"


def _estimert_tid(path: Path) -> str:
    """Grov estimat basert på filstorleik."""
    try:
        mb = path.stat().st_size / 1_000_000
        # ~1 MB/min for MP3 128kbps → small = ~8 min/time opptak
        minutt_opptak = mb / 1.0
        whisper_min   = {"tiny": 0.03, "small": 0.13, "medium": 0.33,
                         "large": 0.75}.get(MODEL_WHISPER, 0.13) * minutt_opptak * 60
        if whisper_min < 1:
            return "under 1 minutt"
        return f"~{int(whisper_min)} minutt"
    except Exception:
        return "ukjend tid"


# ── Hovudfunksjon ──────────────────────────────────────────────────────────────
def lyd_til_notat(lyd_path: Path):
    print(f"\n{'─'*55}")
    print(f"  Ny lydfil: {lyd_path.name}  ({lyd_path.stat().st_size // 1000} kB)")

    # 1. Transkriber
    try:
        transkripsjon, språk = transkriber(lyd_path)
    except Exception as e:
        print(f"  FEIL i Whisper: {e}"); return

    if not transkripsjon.strip():
        print("  FEIL: Tom transkripsjon — sjekk at fila har lyd"); return

    # 2. Vel mappe
    mappe = gjet_mappe(transkripsjon, lyd_path.stem)
    mappe.mkdir(parents=True, exist_ok=True)

    # 3. Send til Claude for strukturering
    # Claude Haiku har 200k token kontekst — sender heile transkripsjonens
    # 90 min førelesing ≈ 11 000 ord ≈ 14 000 tokens, passar fint
    ord_total = len(transkripsjon.split())
    MAX_CHARS = 120_000   # ~30 000 tokens — meir enn nok for 90 min

    if len(transkripsjon) > MAX_CHARS:
        # Svært lange opptak: ta start, midten og slutten
        del_storleik = MAX_CHARS // 3
        utdrag = (
            transkripsjon[:del_storleik]
            + f"\n\n[... midtre del av opptaket ({(len(transkripsjon) - MAX_CHARS) // 1000}k teikn hoppa over) ...]\n\n"
            + transkripsjon[len(transkripsjon)//2 - del_storleik//2 : len(transkripsjon)//2 + del_storleik//2]
            + f"\n\n[... siste del ...]\n\n"
            + transkripsjon[-del_storleik:]
        )
        forkorta = True
    else:
        utdrag   = transkripsjon
        forkorta = False

    prompt = f"""Du er ein Obsidian-notat-assistent for Katchi (ho/hennar), medisinstudent UiO.

IDENTITET:
{critical}

TRANSKRIPSJON av opptak "{lyd_path.stem}" ({ord_total} ord, språk: {språk}):
{utdrag}
{"" if not forkorta else "[... transkripsjon forkorta — originalen er lagra i notatet ...]"}

Lag eit strukturert Obsidian-notat på nynorsk basert på HEILE transkripsjonens innhald.

Bruk dette formatet:
---
tags: [forelesning, lydnotat]
dato: {date.today().isoformat()}
kjelde: {lyd_path.name}
språk: {språk}
---

# {lyd_path.stem}

## 🎯 Hovudpoeng
[3-5 bullet points med det viktigaste frå opptaket]

## 📚 Nøkkelomgrep
[definer dei viktigaste faglege omgrepa — eitt omgrep per linje med definisjon]

## 🗂️ Detaljar
[strukturert gjennomgang med underoverskrifter — syntetiser, ikkje ordrett gjengiving]

## ❓ Spørsmål og gap
[kva var uklart? kva bør utforskast vidare i bøker/SNL/notat?]

## 🔗 Koplingar
[[[wikilenker]] til relaterte notat i Obsidian]

Bruk LaTeX ($...$) for matematiske formlar viss relevant.
Ver konkret, fagleg, og presis. Skriv som om du forklarer til ein medstuderande."""

    print("  Strukturerer med Claude...")
    notat_innhald = ""
    with client.messages.stream(
        model=MODEL, max_tokens=2500,
        messages=[{"role": "user", "content": prompt}]
    ) as stream:
        for chunk in stream.text_stream:
            notat_innhald += chunk
            print(chunk, end="", flush=True)

    print("\n")

    # 4. Legg til full transkripsjon som samansett seksjon nedst
    full_notat = notat_innhald.rstrip() + f"""

---

<details>
<summary>📝 Rå transkripsjon ({ord_total} ord — klikk for å utvide)</summary>

> *Automatisk transkribert med OpenAI Whisper ({MODEL_WHISPER}) · {date.today().isoformat()}*

{transkripsjon}

</details>
"""

    # 5. Skriv notat
    notat_path = mappe / f"{lyd_path.stem}.md"
    notat_path.write_text(full_notat, encoding="utf-8")
    print(f"  ✓ Notat: {notat_path.relative_to(VAULT)}")

    # 6. Arkiver lydfil
    arkiv_path = LYD_ARK / lyd_path.name
    shutil.move(str(lyd_path), str(arkiv_path))
    print(f"  ✓ Arkivert: Lyd_arkiv/{lyd_path.name}")
    print(f"{'─'*55}")


# ── Hovudløkke ─────────────────────────────────────────────────────────────────
sett_filer: set = set()
print(f"Aktiv. Ventar på lydfiler i Lyd_inn/...\n")

try:
    while True:
        time.sleep(POLL)
        for lyd_path in LYD_INN.iterdir():
            if lyd_path.suffix.lower() not in LYDFORMAT:
                continue
            if lyd_path in sett_filer:
                continue
            sett_filer.add(lyd_path)
            try:
                lyd_til_notat(lyd_path)
            except Exception as e:
                print(f"  Feil: {e}")
                import traceback
                traceback.print_exc()
except KeyboardInterrupt:
    print("\nStoppa.")
