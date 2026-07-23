"""
stc_pdf_embed.py — Ciel forstår PDF-ar du dreg inn i eit notat
==============================================================
Dra ein PDF inn i eit forelesnings-notat (Obsidian lagar ![[fila.pdf]]-klamma).
Ciel oppdagar embed-en innan nokre sekund og skriv eit strukturert samandrag
rett inn i SAME notat, under klamma. Ingen kommando, ingen eigen PDF_inn-kanal.

- Idempotent: kvar embed vert berre prosessert éin gong (usynleg HTML-markør).
- Vision-fallback for skanna PDF-ar (ingen tekst-lag).
- Vakt-modus reagerer når du ENDRAR eit notat (dreg PDF inn) — den masse-
  prosesserer ikkje heile vaulten ved oppstart.

Bruk:
  python stc_pdf_embed.py          # vakt (poll kvar 3s)
  python stc_pdf_embed.py --once   # prosesser alle embeds no (backlog/test)

Stopp: Ctrl+C
"""

import os, re, sys, io, time, base64
from pathlib import Path
import anthropic
import pdfplumber

os.environ.setdefault("PYTHONIOENCODING", "utf-8")
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# ── Finn vault (portabelt) ───────────────────────────────────────────────────
_env = os.environ.get("CIEL_VAULT")
if _env:
    VAULT = Path(_env)
else:
    _home   = Path(os.environ.get("USERPROFILE") or Path.home())
    _parent = _home / "OneDrive" / "Obidian stasj"
    _match  = [d for d in _parent.iterdir()
               if "stash" in d.name.lower() and "Copy" not in d.name] if _parent.is_dir() else []
    if not _match:
        print("FEIL: fann ikkje vault-mappa!"); raise SystemExit(1)
    VAULT = _match[0]

MODEL        = os.environ.get("CIEL_MODEL_SIMPLE",  "claude-haiku-4-5")
VISION_MODEL = os.environ.get("CIEL_VISION_MODEL",  "claude-sonnet-4-6")
POLL      = 3
IGNORE    = {".obsidian", ".trash", "PDF_inn", "PDF_arkiv"}
MAX_CHARS = 12000
MAX_PAGES = 25

if not os.environ.get("ANTHROPIC_API_KEY"):
    print("FEIL: ANTHROPIC_API_KEY er ikkje sett!"); raise SystemExit(1)
client = anthropic.Anthropic()

EMBED_RE = re.compile(r'!\[\[([^\]]+\.pdf)\]\]', re.IGNORECASE)

SUMMARY_PROMPT = """Dette er ein PDF (forelesning eller artikkel) for Katchi, medisin- og matematikkstudent ved UiO. Lag eit KORT, strukturert samandrag på nynorsk, meint som innhald i eit Obsidian-callout.

Format (ingen topp-overskrift, berre innhaldet):
- 3–5 kulepunkt med hovudpoenga
- Deretter ei linje "Nøkkelomgrep:" følgt av 3–6 omgrep med kort definisjon
- Til slutt éi linje "Å sjekke:" med det som er uklart / verdt å følgje opp

Bruk LaTeX ($...$) for formlar. Maks 220 ord. Ver fagleg og presis.
Ikkje bruk > (blockquote-teikn) — skriv rein tekst; Ciel legg det i callout sjølv."""


def _finn_pdf(namn: str):
    for p in VAULT.rglob("*.pdf"):
        if any(d in p.parts for d in IGNORE):
            continue
        if p.name.lower() == namn.lower():
            return p
    return None


def _pdf_tekst(path: Path) -> str:
    try:
        t = ""
        with pdfplumber.open(path) as pdf:
            for side in pdf.pages[:MAX_PAGES]:
                s = side.extract_text()
                if s:
                    t += s + "\n\n"
                if len(t) >= MAX_CHARS:
                    break
        return t[:MAX_CHARS].strip()
    except Exception:
        return ""


def _vision_samandrag(path: Path) -> str:
    """Skanna PDF (ingen tekst) → render sider → Claude Vision."""
    import fitz
    from PIL import Image
    blocks = []
    doc = fitz.open(str(path))
    for side in list(doc)[:8]:
        pix = side.get_pixmap(dpi=140)
        img = Image.open(io.BytesIO(pix.tobytes("png")))
        if img.width > 1500:
            img = img.resize((1500, int(img.height * 1500 / img.width)))
        if img.mode != "RGB":
            img = img.convert("RGB")
        buf = io.BytesIO(); img.save(buf, format="JPEG", quality=85)
        blocks.append({"type": "image", "source": {"type": "base64",
                       "media_type": "image/jpeg", "data": base64.b64encode(buf.getvalue()).decode()}})
    doc.close()
    blocks.append({"type": "text", "text": SUMMARY_PROMPT})
    r = client.messages.create(model=VISION_MODEL, max_tokens=1200,
                               messages=[{"role": "user", "content": blocks}])
    return "".join(b.text for b in r.content if getattr(b, "type", "") == "text").strip()


def _lag_samandrag(path: Path) -> str:
    tekst = _pdf_tekst(path)
    if len(tekst) < 60:            # nesten ingen tekst → truleg skanna → Vision
        try:
            return _vision_samandrag(path)
        except Exception as e:
            return f"[Klarte ikkje lese PDF-en (verken tekst eller Vision): {e}]"
    r = client.messages.create(model=MODEL, max_tokens=1000,
        messages=[{"role": "user", "content": f"{SUMMARY_PROMPT}\n\nPDF-TEKST:\n{tekst}"}])
    return "".join(b.text for b in r.content if getattr(b, "type", "") == "text").strip()


def prosesser_notat(path: Path) -> bool:
    try:
        original = path.read_text(encoding="utf-8")
    except Exception:
        return False
    # Vern mot klobbing: hopp over medan stc_agent streamar eit svar (cursor ▊).
    # Neste poll (utan cursor) prosesserer embed-en trygt.
    if "▊" in original:
        return False
    lines = original.splitlines()
    out, done, changed = [], set(), False
    for line in lines:
        out.append(line)
        m = EMBED_RE.search(line)
        if not m:
            continue
        namn   = m.group(1)
        marker = f"<!-- ciel-pdf:{namn} -->"
        if marker in original or namn in done:
            continue                      # allereie prosessert
        pdf = _finn_pdf(namn)
        if not pdf:
            continue
        print(f"  [pdf-embed] {path.name}: les «{namn}»...")
        samandrag = _lag_samandrag(pdf)
        out.append(marker)
        out.append(f"> [!abstract]+ 📄 Ciel las «{namn}»")
        for sl in samandrag.splitlines():
            body = re.sub(r'^\s*>+\s?', '', sl)   # fjern evt. blockquote-teikn frå modellen
            out.append("> " + body if body.strip() else ">")
        out.append("")
        done.add(namn)
        changed = True
    if changed:
        path.write_text("\n".join(out), encoding="utf-8")
        print(f"  ✓ Samandrag lagt inn i {path.relative_to(VAULT)}")
    return changed


def _notat_filer():
    for p in VAULT.rglob("*.md"):
        if any(d in p.parts for d in IGNORE):
            continue
        yield p


def once():
    print("Prosesserer alle PDF-embeds i vaulten (éin gong)...")
    n = 0
    for p in _notat_filer():
        try:
            if EMBED_RE.search(p.read_text(encoding="utf-8", errors="ignore")):
                if prosesser_notat(p):
                    n += 1
        except Exception:
            pass
    print(f"Ferdig. {n} notat oppdatert.")


def vakt():
    print("Ciel PDF-embed-agent startar")
    print(f"Vault     : {VAULT.name}")
    print("Dra ein PDF inn i eit notat (![[fil.pdf]]) — samandrag kjem automatisk")
    print("Ctrl+C for å stoppe\n")
    mtimes: dict = {}
    for p in _notat_filer():                    # seed → ikkje masse-prosesser backlog
        try: mtimes[p] = p.stat().st_mtime
        except Exception: pass
    try:
        while True:
            time.sleep(POLL)
            for p in _notat_filer():
                try:
                    mt = p.stat().st_mtime
                except Exception:
                    continue
                if mtimes.get(p) == mt:
                    continue
                mtimes[p] = mt
                try:
                    txt = p.read_text(encoding="utf-8", errors="ignore")
                except Exception:
                    continue
                if EMBED_RE.search(txt):
                    prosesser_notat(p)
    except KeyboardInterrupt:
        print("\nStoppa.")


if __name__ == "__main__":
    if "--once" in sys.argv:
        once()
    else:
        vakt()
