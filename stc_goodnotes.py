"""
stc_goodnotes.py — GoodNotes (handskrift) → Obsidian via Claude Vision
======================================================================
GoodNotes har ingen open API, og notata er handskrift (blekk), ikkje tekst.
Broa er enkel: eksporter GoodNotes-sider som PDF eller bilete inn i ei synka
mappe, så les Ciel handskrifta med Claude Vision og lagar eit strukturert
Obsidian-notat på nynorsk.

Flyt:
  1. Dropp/eksporter PDF eller bilete i  AI/GoodNotes/inn/   (synka via vaulten)
  2. Renderar sider → sender til Claude Vision → transkriberer handskrift
  3. Strukturerer til Obsidian-notat (same format som lyd/PDF-agentane)
  4. Skriv notat til rett fagmappe, arkiverer originalen

Bruk:
  python stc_goodnotes.py            → vakt-modus (overvaker inn/)
  python stc_goodnotes.py <fil>      → prosesser éi fil med ein gong (testbart)

Stopp: Ctrl+C

ÆRLEG: bilete av handskrifta blir sende til Anthropic (Claude Vision) — same som
PDF/lyd-agentane (sjå SPEC §14). Kvaliteten avheng av kor leseleg handskrifta er;
uleselege parti vert markerte, ikkje gjetta.
"""

import os, sys, io, time, base64, shutil
from datetime import date
from pathlib import Path

os.environ.setdefault("PYTHONIOENCODING", "utf-8")
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import anthropic
import fitz                      # PyMuPDF — renderar PDF-sider til bilete
from PIL import Image
from stc_agent import VAULT       # portabel vault-deteksjon (éin sanningskjelde)

# ── Konfigurasjon ─────────────────────────────────────────────────────────────
INN   = VAULT / "AI" / "GoodNotes" / "inn"
ARK   = VAULT / "AI" / "GoodNotes" / "arkiv"
MODEL = os.environ.get("CIEL_VISION_MODEL", "claude-sonnet-4-6")  # sterk på handskrift
POLL  = 5
FORMATS   = {".pdf", ".png", ".jpg", ".jpeg", ".webp"}
MAX_PAGES = 12        # maks sider per notat (held token-bruk fornuftig)
MAX_W     = 1500      # nedskaler breie bilete → billegare, framleis leseleg

INN.mkdir(parents=True, exist_ok=True)
ARK.mkdir(parents=True, exist_ok=True)

if not os.environ.get("ANTHROPIC_API_KEY"):
    print("FEIL: ANTHROPIC_API_KEY er ikkje sett!"); raise SystemExit(1)

client = anthropic.Anthropic()

try:
    critical = (VAULT / "CRITICAL_FACTS.md").read_text(encoding="utf-8")[:400]
except Exception:
    critical = "Katchi (Karthik Senthil Ganesh), medisinstudent UiO."

_STUDIE  = VAULT / "Studie"
_MEDISIN = _STUDIE / "Medisin"


def gjet_mappe(tekst: str, filnamn: str) -> Path:
    """Rut notatet til rett fagmappe basert på innhald (som lyd/PDF-agentane)."""
    t = (tekst + " " + filnamn).lower()
    if any(w in t for w in ["statistikk", "stk", "sannsyn", "fordeling", "konfidensintervall"]):
        return _STUDIE / "Honours og Matte" / "Semesterer"
    if any(w in t for w in ["nevrologi", "nerve", "hjerne", "aksjonspotensial", "synapse"]):
        return _MEDISIN / "Nevrologi"
    if any(w in t for w in ["celle", "membran", "dna", "protein", "metabolisme", "glykolyse", "mitokondrie"]):
        return _MEDISIN / "Modul 1" / "Blokk 2" / "CelleBio"
    if any(w in t for w in ["lsb", "seminargruppe", "gruppeundervisning"]):
        return _MEDISIN / "Modul 1" / "Blokk 2" / "LSB"
    if any(w in t for w in ["histologi", "vev", "epitel", "biopsi"]):
        return _MEDISIN / "Modul 1" / "Blokk 2"
    if any(w in t for w in ["matte", "lineær", "vektor", "matrise", "kalkulus", "derivasjon", "integrasjon"]):
        return _STUDIE / "Honours og Matte"
    if any(w in t for w in ["anatomi", "fysiologi", "biokjemi", "farmakologi", "patologi", "immunologi"]):
        return _MEDISIN / "Modul 1"
    return _MEDISIN / "Medisin Forelesninger"


def _vault_mapper() -> list[Path]:
    """Hent dei EKTE mappene i vaulten (så ruting tilpassar seg din struktur)."""
    skip_parts = {".obsidian", ".trash", "AI", "Usikkere notat ord"}
    ut = []
    for d in VAULT.rglob("*"):
        if not d.is_dir():
            continue
        parts = d.relative_to(VAULT).parts
        if any(s in parts for s in skip_parts):
            continue
        if d.name.lower() in {"inn", "arkiv"} or "arkiv" in d.name.lower():
            continue
        if len(parts) > 4:          # ikkje for djupt nøsta
            continue
        ut.append(d)
    return ut


def vel_mappe(note: str, filnamn: str) -> Path:
    """Lar Ciel velje den BEST passande EKSISTERANDE mappa basert på innhaldet.
    Fell tilbake til nøkkelord-heuristikken om noko feilar."""
    folders = _vault_mapper()
    if not folders:
        return gjet_mappe(note, filnamn)
    rel = [str(f.relative_to(VAULT)).replace("\\", "/") for f in folders]
    listing = "\n".join(rel)
    prompt = f"""Eksisterande mapper i Obsidian-vaulten:
{listing}

Eit nytt fagnotat (filnamn: "{filnamn}") har dette innhaldet:
{note[:1000]}

Kva mappe passar BEST for dette notatet? Svar med NØYAKTIG éin av stiane frå lista over — berre stien, ingenting anna."""
    try:
        resp = client.messages.create(
            model="claude-haiku-4-5", max_tokens=60,
            messages=[{"role": "user", "content": prompt}],
        )
        ans = "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")
        ans = ans.strip().strip("`").splitlines()[0].strip() if ans.strip() else ""
        for f, r in zip(folders, rel):
            if ans == r:
                print(f"  [ruting] Ciel valde: {r}")
                return f
    except Exception as e:
        print(f"  [ruting] fall tilbake til nøkkelord ({e})")
    return gjet_mappe(note, filnamn)


def _img_to_b64(img: Image.Image) -> str:
    """Nedskaler + komprimer til JPEG base64 (billegare Vision-kall)."""
    if img.width > MAX_W:
        h = int(img.height * MAX_W / img.width)
        img = img.resize((MAX_W, h))
    if img.mode != "RGB":
        img = img.convert("RGB")
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return base64.b64encode(buf.getvalue()).decode()


def _sider(path: Path) -> list[Image.Image]:
    """Hent sider som bilete — frå PDF (render) eller eit reint biletfil."""
    if path.suffix.lower() == ".pdf":
        imgs = []
        doc = fitz.open(str(path))
        for pg in list(doc)[:MAX_PAGES]:
            pix = pg.get_pixmap(dpi=150)
            imgs.append(Image.open(io.BytesIO(pix.tobytes("png"))))
        doc.close()
        return imgs
    return [Image.open(path)]


PROMPT = """Du er Ciel, kunnskapsassistenten til Katchi (ho/hennar), medisin- og matematikkstudent ved UiO.

Bileta er HANDSKRIVNE notat (frå GoodNotes). Oppgåva di:
1. Les og tolk handskrifta så trufast du kan (internt). Marker uleselege parti med [uleseleg], aldri gjett.
2. Lag eit strukturert Obsidian-notat på NYNORSK basert på innhaldet — ikkje ordrett, men syntetisert.

VIKTIG: Returner BERRE sjølve notatet — start med YAML-frontmatter (---). Inga innleiing,
inga "transkripsjon"-seksjon, og IKKJE pakk svaret i ```-kodeblokk. Berre rein markdown.

Bruk dette formatet:
---
tags: [goodnotes, handskrift]
dato: {dato}
kjelde: {kjelde}
---

# {tittel}

## 🎯 Hovudpoeng
[3-5 punkt med det viktigaste]

## 🗂️ Detaljar
[strukturert gjennomgang med underoverskrifter]

## 🔢 Formlar / nøkkelomgrep
[LaTeX ($...$) for matematikk; definer viktige omgrep]

## ❓ Uklart / å sjekke
[kva var uleseleg eller treng oppfølging]

Ver fagleg og presis. Bruk LaTeX for formlar der det passar."""


def til_notat(path: Path):
    print(f"\n{'─'*55}\n  GoodNotes: {path.name}")
    try:
        sider = _sider(path)
    except Exception as e:
        print(f"  FEIL ved opning: {e}"); return
    if not sider:
        print("  Ingen sider funne."); return
    print(f"  {len(sider)} side(r) → Claude Vision ({MODEL})...")

    blocks = []
    for img in sider:
        blocks.append({
            "type": "image",
            "source": {"type": "base64", "media_type": "image/jpeg", "data": _img_to_b64(img)},
        })
    prompt = PROMPT.format(dato=date.today().isoformat(), kjelde=path.name, tittel=path.stem)
    blocks.append({"type": "text", "text": prompt})

    try:
        resp = client.messages.create(
            model=MODEL, max_tokens=2500,
            messages=[{"role": "user", "content": blocks}],
        )
        notat = "".join(b.text for b in resp.content if getattr(b, "type", "") == "text").strip()
    except Exception as e:
        print(f"  FEIL i Vision-kall: {e}"); return

    if not notat:
        print("  Tomt svar frå Vision."); return

    mappe = vel_mappe(notat, path.stem)
    mappe.mkdir(parents=True, exist_ok=True)
    notat_path = mappe / f"{path.stem}.md"
    notat_path.write_text(notat, encoding="utf-8")
    print(f"  ✓ Notat: {notat_path.relative_to(VAULT)}")

    # Arkiver originalen så han ikkje vert prosessert på nytt
    try:
        shutil.move(str(path), str(ARK / path.name))
        print(f"  ✓ Arkivert: AI/GoodNotes/arkiv/{path.name}")
    except Exception as e:
        print(f"  (kunne ikkje arkivere: {e})")
    print(f"{'─'*55}")


def vakt():
    print("Ciel GoodNotes-agent startar")
    print(f"Vault     : {VAULT.name}")
    print(f"Overvaker : {INN}")
    print(f"Vision    : {MODEL}")
    print("Eksporter GoodNotes som PDF/bilete til inn/ — notat kjem automatisk")
    print("Ctrl+C for å stoppe\n")
    sett: set = set()
    try:
        while True:
            time.sleep(POLL)
            for p in INN.iterdir():
                if p.suffix.lower() not in FORMATS or p in sett:
                    continue
                sett.add(p)
                try:
                    til_notat(p)
                except Exception as e:
                    print(f"  Feil: {e}")
    except KeyboardInterrupt:
        print("\nStoppa.")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        til_notat(Path(sys.argv[1]))   # éin fil, éin gong (testbart)
    else:
        vakt()
