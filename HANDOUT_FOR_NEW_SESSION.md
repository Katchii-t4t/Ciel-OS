# 🌙 Project Ciel — Complete Handout for New Claude Code Session
> Read this entire document before doing anything. Everything you need is here.

---

## 1. WHO IS THE USER

**Name:** Katchi (Karthik Senthil Ganesh), goes by "Katchi"  
**Pronouns:** ho/hennar  
**Age:** 19  
**Studies:** Medicine + Mathematics (Honours), University of Oslo (UiO)  
**Activities:** EPIC AI research project, CogPrint website, NORA Summer School 2026 (Module K — SNN)  
**Languages:** Norwegian Nynorsk (written in Obsidian), English (spoken to Claude)  
**GitHub:** https://github.com/Katchii-t4t  
**Repo:** https://github.com/Katchii-t4t/Ciel-OS (private)

---

## 2. WHAT PROJECT CIEL IS

Ciel is a personal, ambient AI assistant integrated into Obsidian, with a long-term vision of becoming a full Android launcher ("Ciel OS") on a Samsung Galaxy Tab S10+. The current seed system runs on PC and is already functional.

**The felt experience (target):** "JARVIS, but real, and built within the limits of 2026 consumer hardware."

**Current state (Phase 0 complete, Phase 1 next):**
- Python agents running on PC watch Obsidian vault every 3 seconds
- User types `Ciel: ""question""` in any Obsidian note → gets AI answer with typewriter effect inline
- Norwegian lectures auto-transcribed with NB-Whisper → structured Nynorsk notes
- All code version-controlled at https://github.com/Katchii-t4t/Ciel-OS

---

## 3. NON-NEGOTIABLE SECURITY RULES (never violate these)

1. **ANTHROPIC_API_KEY must NEVER be hardcoded in any file.** It is stored as a Windows User environment variable only.
2. **Clients (tablet, phone) never call Anthropic directly.** Only the PC backend calls the API.
3. If you need to use the key in code, always read it via `os.environ.get("ANTHROPIC_API_KEY")`.

---

## 4. HARDWARE & ENVIRONMENT

**PC (the brain):**
- Windows 11, `C:\Users\Karthik\`
- Python via Anaconda: `C:\Users\Karthik\anaconda3\`
- All Ciel code lives in: `C:\Users\Karthik\.claude\`
- Code repo copy lives in: `C:\Users\Karthik\ciel\`
- Key packages installed: `anthropic`, `transformers`, `accelerate`, `torch`, `pdfplumber`, `chess`, `requests`

**Obsidian Vault:**
- Path: `C:\Users\Karthik\OneDrive\Obidian stasj\Katchi's stash\`
- Auto-detected by scripts using: `[d for d in _parent.iterdir() if "stash" in d.name.lower() and "Copy" not in d.name]`
- Synced via OneDrive to `sgkarthik04@gmail.com`

**Vault folder structure (confirmed):**
```
Katchi's stash/                    ← VAULT root
├── _DAGLEG.md                     ← daily briefing (auto-generated)
├── CRITICAL_FACTS.md              ← user context for Claude
├── AI/
│   └── Lyd/
│       ├── Lyd_inn/               ← drop audio files here
│       └── Lyd_arkiv/             ← archived audio
├── Extracurricular/
│   └── Chess/                     ← chess games + SVG images
│       └── bilete/
├── PDF_inn/                       ← drop PDFs here
├── PDF_arkiv/                     ← archived PDFs
└── Studie/
    ├── Honours og Matte/
    │   ├── Fysikk/
    │   └── Semesterer/
    └── Medisin/
        ├── Medisin Forelesninger/  ← default lecture destination
        │   ├── Semester 1/
        │   └── Semester 2/
        ├── Modul 1/
        │   ├── Blokk 1/
        │   ├── Blokk 2/
        │   │   ├── CelleBio/
        │   │   ├── LSB/
        │   │   └── Fagomgrepp/
        │   └── Exphil/
        └── Nevrologi/
```

**Tablet (new — just arrived):**
- Samsung Galaxy Tab S10+ (SM-X820NZAREUB)
- Android / One UI, English language settings
- ADB connected to PC (device ID: R5GYC3QJYJY)
- Obsidian installed, vault copied via `adb push` to `/sdcard/Documents/Katchi's stash/`
- Syncthing installed on PC (not yet configured on tablet)
- Flutter SDK downloading (700 MB, may or may not be complete)

---

## 5. ALL CURRENT CIEL COMMANDS

| Command | Function |
|---------|----------|
| `Ciel: ""question""` | General answer from vault + Claude |
| `Ciel-A: ""question""` | Deep answer: SNL + Wikipedia + PubMed + vault |
| `Ciel-sjekk: ""text""` | Fact-check against SNL/Wikipedia |
| `Ciel-diagram: ""topic""` | Generate Mermaid diagram |
| `Ciel-skriv: ""text""` | Rewrite/correct text in Nynorsk |
| `Ciel-kryssref: ""topic""` | Find contradictions across vault notes |
| `Ciel-latex: ""formula""` | Explain with LaTeX math |
| `Ciel-eksamen: ""topic""` | Exam gap analysis |
| `Ciel-forslag: ""question""` | Suggest note connections |
| `Ciel-chess: [PGN]` | Analyse chess game (white perspective) |
| `Ciel-chess-W: [PGN]` | Analyse chess game (white perspective) |
| `Ciel-chess-B: [PGN]` | Analyse chess game (black perspective) |

**Important note on syntax:** Commands require double-quotes: `Ciel: ""your question here""`. Obsidian auto-pairs `"` so the user only needs to press `"` once at each end. The agent waits for the closing `""` before processing (this is how it knows the question is finished).

---

## 6. RUNNING AGENTS

**Normal startup (autostart via VBS):**
```
C:\Users\Karthik\.claude\start_ciel.vbs
```
This starts stc_agent.py, stc_pdf.py, and stc_lyd.py invisibly in background.

**Manual startup in PowerShell:**
```powershell
$env:ANTHROPIC_API_KEY = [System.Environment]::GetEnvironmentVariable("ANTHROPIC_API_KEY", "User")
cd C:\Users\Karthik\.claude
python stc_agent.py    # main agent
python stc_lyd.py      # audio transcription
python stc_pdf.py      # PDF processing
```

**Autostart location:** `shell:startup` folder (Win+R → shell:startup)

---

## 7. COMPLETE SOURCE CODE — ALL FILES

### 7.1 `stc_agent.py` — Main Agent

```python
"""
Ciel-agent v3 — Utvida vault-assistent
======================================
Overvaker alle .md-filer i vaulten kvart 3. sekund.
Streaming-svar (skrivemaskin-effekt) direkte i Obsidian.

Prefiks:
  Ciel:           → Svar på spørsmål frå vaulten
  Ciel-sjekk:     → Faktasjekk mot SNL + Wikipedia
  Ciel-diagram:   → Generer Mermaid-diagram (Obsidian rendrar automatisk)
  Ciel-skriv:     → Omskriv og rettskrive tekst på nynorsk
  Ciel-kryssref:  → Finn motstridande info på tvers av notat
  Ciel-latex:     → Forklar med LaTeX-matematikk og formlar
  Ciel-eksamen:   → Eksamensgap-analyse mot pensum
  Ciel-forslag:   → Finn relaterte notat og foreslå koplingar
  Ciel-A:         → A+ spørsmål: djupdykk med SNL + Wikipedia + PubMed

Bruk: python stc_agent.py
Stopp: Ctrl+C
"""

import os, re, sys, time, requests, anthropic
import chess, chess.pgn, chess.svg, io
import pdfplumber
from datetime import date
from pathlib import Path

os.environ.setdefault("PYTHONIOENCODING", "utf-8")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ── Konfigurasjon ──────────────────────────────────────────────────────────────
_parent = Path("C:/Users/Karthik/OneDrive/Obidian stasj")
_match  = [d for d in _parent.iterdir() if "stash" in d.name.lower() and "Copy" not in d.name]
if not _match:
    print("FEIL: Fann ikkje vault-mappa!"); raise SystemExit(1)

VAULT        = _match[0]
MODEL        = "claude-haiku-4-5"
POLL_SECS    = 3
STREAM_CHUNK = 12

IGNORE  = {"Usikkere notat ord", ".obsidian", ".trash"}
STOPORD = {"kva","kan","om","er","og","til","frå","fra","med","som","det","dei",
           "har","for","veit","meg","seg","kven","korleis","ein","eit","den",
           "ikkje","enn","men","hva","hvordan","ikke","deg","jeg","min","din"}

PREFIXES = ["Ciel-sjekk:", "Ciel-diagram:", "Ciel-skriv:", "Ciel-kryssref:",
            "Ciel-latex:", "Ciel-eksamen:", "Ciel-forslag:", "Ciel-A:",
            "Ciel-chess-W:", "Ciel-chess-B:", "Ciel-chess:", "Ciel:"]

CHESS_PREFIXES = {"Ciel-chess:", "Ciel-chess-W:", "Ciel-chess-B:"}
CHESS_DIR = VAULT / "Extracurricular" / "Chess"

FAN_MAP  = {'K': '♔', 'Q': '♕', 'R': '♖', 'B': '♗', 'N': '♘'}

def to_fan(san):
    if san and san[0] in FAN_MAP:
        return FAN_MAP[san[0]] + san[1:]
    return san

PIECE_VAL = {chess.PAWN: 1, chess.KNIGHT: 3, chess.BISHOP: 3,
             chess.ROOK: 5, chess.QUEEN: 9}

def mat_score(board):
    s = 0
    for pt, val in PIECE_VAL.items():
        s += val * len(board.pieces(pt, chess.WHITE))
        s -= val * len(board.pieces(pt, chess.BLACK))
    return s

BOARD_COLORS = {
    "square light": "#F0D9B5",
    "square dark":  "#B58863",
    "margin":       "#2C1810",
    "coord":        "#E8D5B0",
}

if not os.environ.get("ANTHROPIC_API_KEY"):
    print("FEIL: ANTHROPIC_API_KEY er ikkje sett!"); raise SystemExit(1)

client = anthropic.Anthropic()

# ── Vault-søk ─────────────────────────────────────────────────────────────────
def search_vault(terms, exclude_path=None, top_n=5):
    hits = []
    seen = set()
    for path in VAULT.rglob("*.md"):
        if any(d in path.parts for d in IGNORE): continue
        if path.name.startswith("_"): continue
        if exclude_path and path == exclude_path: continue
        try:
            txt = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        score = sum(txt.lower().count(t) for t in terms)
        if score > 0 and path.stem not in seen:
            seen.add(path.stem)
            hits.append((score, path.stem, txt[:700].strip()))
    hits.sort(reverse=True)
    return hits[:top_n]

def get_critical():
    try:
        return (VAULT / "CRITICAL_FACTS.md").read_text(encoding="utf-8")[:500]
    except Exception:
        return "Karthik Senthil Ganesh, medisinstudent UiO."

def hits_to_ctx(hits):
    return "\n\n---\n\n".join(f"### {stem}\n{txt}" for _, stem, txt in hits) or "Ingen treff i vaulten."

def get_current_note_ctx(pre):
    """Returns content of current note ABOVE the Ciel: line (max 4000 chars).
    Filters out previous Ciel answers so Claude doesn't re-read its own output."""
    linjer = pre[:-1]
    reinskt = []
    i_svar  = False
    for linje in linjer:
        s = linje.strip()
        if s.startswith("**Svar ("):
            i_svar = True
        if not i_svar:
            reinskt.append(linje)
        if i_svar and s and not s.startswith((">", "▊", "**Svar", "---")):
            if not any(s.startswith(p) for p in PREFIXES):
                i_svar = False
                reinskt.append(linje)
    tekst = "\n".join(reinskt).strip()
    return tekst[-4000:] if len(tekst) > 4000 else tekst

# ── PDF-embedding ──────────────────────────────────────────────────────────────
def _finn_pdf(filnamn):
    for path in VAULT.rglob("*.pdf"):
        if path.name.lower() == filnamn.lower():
            return path
    return None

def _les_pdf_tekst(path, maks_teikn=8000):
    try:
        tekst = ""
        with pdfplumber.open(path) as pdf:
            for side in pdf.pages[:20]:
                side_tekst = side.extract_text()
                if side_tekst:
                    tekst += side_tekst + "\n\n"
                if len(tekst) >= maks_teikn:
                    break
        return tekst[:maks_teikn].strip()
    except Exception as e:
        return f"[Klarte ikkje lese PDF: {e}]"

def hent_pdf_kontekst(linjer):
    delar = []
    sett  = set()
    for linje in linjer:
        for filnamn in re.findall(r'!\[\[([^\]]+\.pdf)\]\]', linje, re.IGNORECASE):
            if filnamn in sett:
                continue
            sett.add(filnamn)
            pdf_path = _finn_pdf(filnamn)
            if pdf_path:
                tekst = _les_pdf_tekst(pdf_path)
                delar.append(f"=== PDF: {filnamn} ===\n{tekst}")
    return "\n\n".join(delar)

# ── Web-kjelder ───────────────────────────────────────────────────────────────
def fetch_snl(term):
    try:
        r = requests.get("https://snl.no/api/v1/search",
            params={"query": term, "limit": 1}, timeout=5)
        results = r.json()
        if not results: return None
        headword    = results[0].get("headword", term)
        article_url = results[0].get("article_url_json")
        if not article_url: return None
        article = requests.get(article_url, timeout=5).json()
        body    = re.sub(r"<[^>]+>", " ", article.get("body", ""))
        body    = re.sub(r"\s+", " ", body).strip()[:1200]
        if body: return f"SNL — {headword}:\n{body}"
    except Exception:
        pass
    return None

def fetch_wikipedia(term):
    for lang in ("no", "en"):
        try:
            r = requests.get(
                f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{term.replace(' ', '_')}",
                timeout=5)
            if r.status_code == 200:
                extract = r.json().get("extract", "")
                if extract:
                    return f"Wikipedia ({lang}) — {term}:\n{extract[:1200]}"
        except Exception:
            pass
    return None

def fetch_pubmed(query):
    try:
        search = requests.get(
            "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi",
            params={"db": "pubmed", "term": query, "retmax": 3,
                    "retmode": "json", "sort": "relevance"}, timeout=8)
        ids = search.json().get("esearchresult", {}).get("idlist", [])
        if not ids: return ""
        fetch = requests.get(
            "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi",
            params={"db": "pubmed", "id": ",".join(ids),
                    "rettype": "abstract", "retmode": "text"}, timeout=10)
        return f"PubMed ({len(ids)} artiklar):\n{fetch.text[:2500]}"
    except Exception:
        return ""

# ── Streaming til fil ─────────────────────────────────────────────────────────
def stream_to_file(filepath, pre_lines, post_lines, header, prompt, max_tokens=900):
    full_text    = ""
    chunk_buffer = ""

    def write_current(cursor=True):
        suffix = ["▊"] if cursor else []
        lines  = [header] + full_text.split("\n") + suffix + [""]
        filepath.write_text(
            "\n".join(pre_lines + lines + post_lines),
            encoding="utf-8"
        )

    write_current(cursor=True)

    try:
        with client.messages.stream(
            model=MODEL, max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}]
        ) as stream:
            for text in stream.text_stream:
                chunk_buffer += text
                if len(chunk_buffer) >= STREAM_CHUNK:
                    full_text   += chunk_buffer
                    chunk_buffer = ""
                    write_current(cursor=True)
                    time.sleep(0.03)
        if chunk_buffer:
            full_text += chunk_buffer
    except Exception as e:
        full_text += f"\n\n[Feil: {e}]"

    write_current(cursor=False)
    return full_text

# ── All handlers are defined in the actual file —
# See C:\Users\Karthik\.claude\stc_agent.py for complete handler implementations
# (handle_stc, handle_sjekk, handle_diagram, handle_skriv, handle_kryssref,
#  handle_latex, handle_eksamen, handle_forslag, handle_A, handle_chess)
```

> **Note:** The full 1003-line stc_agent.py is at `C:\Users\Karthik\.claude\stc_agent.py` and `C:\Users\Karthik\ciel\stc_agent.py`. Read it directly — do not recreate it.

---

### 7.2 `stc_lyd.py` — Audio Transcription Agent

**Key facts:**
- Uses `NbAiLab/nb-whisper-medium` (Norwegian-optimised, ~1.5 GB, downloads automatically first run)
- Watches `VAULT/AI/Lyd/Lyd_inn/` every 5 seconds
- Transcribes → sends to Claude → writes structured Nynorsk note → archives audio to `Lyd_arkiv/`
- Uses `chunk_length_s=30` for 2+ hour recordings
- Forces Norwegian: `generate_kwargs={"language": "no", "task": "transcribe"}`
- `gjet_mappe()` routes notes to correct vault folders based on keywords

> **Note:** Full file at `C:\Users\Karthik\.claude\stc_lyd.py`. Do not recreate.

---

### 7.3 `stc_pdf.py` — PDF Processing Agent

**Key facts:**
- Watches `VAULT/PDF_inn/` every 5 seconds
- Uses `pdfplumber` to extract text (max 20 pages, 8000 chars)
- Sends to Claude → structured Obsidian note → archives to `PDF_arkiv/`
- `gjet_mappe()` routes to correct folder

> **Note:** Full file at `C:\Users\Karthik\.claude\stc_pdf.py`. Do not recreate.

---

### 7.4 `stc_autolink.py` — Auto-linking Agent

**Key facts:**
- Run manually: `python stc_autolink.py` (dry-run preview)
- Run with writes: `python stc_autolink.py --skriv`
- Two functions: (1) explicit linking — finds note names mentioned without `[[]]` and adds them; (2) semantic linking — finds notes with keyword overlap and adds "Relaterte notat" section
- Also runs automatically as part of `stc_agent.py` main loop on every changed file

> **Note:** Full file at `C:\Users\Karthik\.claude\stc_autolink.py`. Do not recreate.

---

### 7.5 `stc_morning.py` — Daily Morning Briefing

**Key facts:**
- Run manually or via Windows Task Scheduler at 07:30
- Analyses vault: last week's active notes, forgotten notes (30+ days), statistics
- Writes to `VAULT/_DAGLEG.md`
- Motivating Nynorsk briefing: what you worked on, what to review, 3 concrete priorities

> **Note:** Full file at `C:\Users\Karthik\.claude\stc_morning.py`. Do not recreate.

---

### 7.6 `start_ciel.vbs` — Invisible Autostart

```vbs
' start_ciel.vbs — Startar alle Ciel-agentar heilt usynleg
Dim sh
Set sh = CreateObject("WScript.Shell")

Dim apiKey
apiKey = sh.ExpandEnvironmentStrings("%ANTHROPIC_API_KEY%")

sh.Environment("USER").Item("ANTHROPIC_API_KEY") = apiKey
sh.Environment("USER").Item("KMP_DUPLICATE_LIB_OK") = "TRUE"
sh.Environment("USER").Item("PYTHONIOENCODING") = "utf-8"

Dim py
py = "C:\Users\Karthik\anaconda3\pythonw.exe"

Dim base
base = "C:\Users\Karthik\.claude\"

sh.Run Chr(34) & py & Chr(34) & " """ & base & "stc_agent.py""", 0, False
sh.Run Chr(34) & py & Chr(34) & " """ & base & "stc_pdf.py""",   0, False
sh.Run Chr(34) & py & Chr(34) & " """ & base & "stc_lyd.py""",   0, False

Set sh = Nothing
```

---

## 8. NEXT STEPS — WHAT TO BUILD NOW

### Immediate (this session)

**Step 1: Finish Syncthing setup (10 min)**
Syncthing is installed on PC (`syncthing` command works). Tablet needs the Android app. Once both run:
- PC: open `http://localhost:8384` in browser → Add Remote Device → enter tablet's Syncthing ID
- Tablet: Syncthing app → share the vault folder → accept on PC
- This replaces the manual `adb push` for vault sync.

**Step 2: Check Flutter installation**
Flutter was downloading (~700 MB) when Katchi went to sleep. Check if it completed:
```powershell
$env:PATH = [System.Environment]::GetEnvironmentVariable("PATH", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("PATH", "User")
flutter --version
flutter doctor
```
If not complete, re-download.

### Phase 1 — FastAPI Backend (the real next milestone)

Wrap existing Python scripts in a FastAPI server so the tablet can talk to the PC via HTTP/WebSocket.

**Target API contract:**
```
POST /api/ask           → sends question, returns streaming answer
POST /api/transcribe    → sends audio, returns transcription
GET  /api/vault/notes   → returns recent notes
GET  /api/state         → returns current mode (ambient/solo/etc.)
WS   /ws/stream         → streaming token-by-token typewriter
WS   /ws/events         → push events (new note, mode change, etc.)
```

**Key implementation notes:**
- FastAPI + Uvicorn
- All existing handler functions (`handle_stc`, `handle_A`, etc.) stay as-is — just wrap them
- Streaming via WebSocket: send one JSON `{"token": "..."}` per chunk
- Start as background service on PC login (add to start_ciel.vbs)
- CORS enabled for tablet IP

**File to create:** `C:\Users\Karthik\ciel\ciel_server.py`

### Phase 2 — Flutter Tablet App

After Phase 1, build a Flutter app that:
1. Connects to PC over WiFi (or Tailscale for remote)
2. Shows a text input to ask Ciel questions
3. Displays streaming answer with typewriter effect
4. Lists recent vault notes
5. Works offline (shows cached notes, queues questions)

**Key Flutter files to create:**
- `ciel_app/lib/main.dart`
- `ciel_app/lib/screens/home.dart`
- `ciel_app/lib/services/ciel_api.dart` (WebSocket client)

---

## 9. FULL CIEL OS ROADMAP

```
Phase 0 — Foundations          ← COMPLETE ✅
  Python agents running, vault integration working

Phase 1 — Backend API          ← NEXT
  FastAPI wrapping existing scripts
  Full vault triggers accessible via REST/WebSocket

Phase 2 — Tablet client
  Flutter app: text ask, streaming typewriter, note view

Phase 3 — Voice
  STT (tablet mic → PC NB-Whisper → text)
  TTS (Piper local / ElevenLabs premium → audio to tablet)
  Wake word gate
  Voice auth ritual (SpeechBrain — "Welcome back, Dr. Katchi")

Phase 4 — Launcher & Orb
  Flutter app registers as Android HOME intent
  Crystalline star-orb animation (CustomPainter, 60fps)
  Mode colours: Gold=ambient, Blue=solo, Green=social, Purple=lecture, Red=wind-down
  Girl mode: trans-flag particle bands (auto-trigger on personal/feminine context)

Phase 5 — Proactive + Tracker
  Morning/evening briefings (spoken in Solo, card in Social)
  Daily score with wellbeing guardrail (rest = positive metric)
  Doom-scroll guard (UsageStats API — Observer/Soft/Strict levels)
  Health Connect integration (Galaxy Watch HR, HRV, sleep)
  HRT cycle tracking + correlation with performance

Phase 6 — Lecture + Ink + Assist
  Auto-transcription in Lecture mode (purple orb)
  Discreet answer cards for room questions
  S Pen → ML Kit (text) + Claude Vision (math) → LaTeX
  Meeting assist (live discreet cards)

Phase 7 — Music + Screen
  Spotify API on-command + auto playlists
  PC screen capture + Tesseract/Claude Vision

Phase 8 — SNN (post NORA 2026)
  Norse/snnTorch for speech/noise gate, context classification
  Online adaptation via e-prop

Phase 9+ — Glasses
  Ray-Ban Meta on-demand frame capture
  Shopping price-check, grocery, style assist
```

**v1 JARVIS acceptance criteria:**
- Orb on home screen with mode colours ✓ (Phase 4)
- Voice in/out, Ciel's voice ✓ (Phase 3)
- Voice recognises Katchi, says "Dr. Katchi" ✓ (Phase 3)
- Lecture mode: records, transcribes, answer cards ✓ (Phase 6)
- Daily briefing + score ✓ (Phase 5)
- Syncs PC↔tablet, offline graceful degradation ✓ (Phase 1-2)

---

## 10. VISUAL IDENTITY — THE CIEL ORB

**Design reference:** Raphael from Tensura (sharp, geometric, omniscient crystalline core)

**Orb anatomy:**
- Core: white-bright pinpoint + 4-pointed crystalline star (slow rotation)
- Inner haze: particles close to core (depth + volume)
- Bubble shell: dense ring of particles, not perfect circle, breathes/warps
- Outer wisps: sparse slow particles, increasingly chaotic outward
- Long star rays: 8 rays through darkness, thin, precise

**Mode colours:**
```
Ambient    #EF9F27  Gold/amber    — default, Ciel's identity colour
Solo       #85B7EB  Ice blue      — JARVIS-active
Social     #97C459  Muted green   — silent, discreet
Lecture    #AFA9EC  Violet/purple — focused, recording
Wind-down  #F09595  Soft red      — evening, rest
```

**Background:** Pure black `#000000` (AMOLED off-pixels)

**Girl mode:** Particles gather into trans flag bands (blue/white/pink), core stays white. Auto-triggers on HRT/estrogen/feminine personal topics. Returns to gold.

**Ciel's voice:** Calm, slightly raspy, British female accent, never hurried. "Good morning, Dr. Katchi. You have a cell biology lecture in forty minutes."

---

## 11. PERSONALITY & IDENTITY

- **Name:** Ciel (French for "sky")
- **Addresses user as:** Dr. Katchi
- **Written answers:** Norwegian Nynorsk, max 300 words normal / professor-style with sources for deep answers
- **Spoken:** English, British accent, calm and authoritative
- **Never says** "Would you like me to..." unprompted
- **Every word is deliberate** — never filler, never hurried

---

## 12. TOOLS & INFRASTRUCTURE INSTALLED

| Tool | Location | Status |
|------|----------|--------|
| Python (Anaconda) | `C:\Users\Karthik\anaconda3\` | ✅ |
| ADB (Android Debug Bridge) | winget installed | ✅ |
| GitHub CLI (gh) | winget installed | ✅ (needs `gh auth login`) |
| Syncthing | winget installed | ✅ PC side, ⚠️ tablet side pending |
| Flutter SDK | `C:\Users\Karthik\flutter.zip` | ⚠️ downloading/extracting |
| Git | installed | ✅ |
| NB-Whisper model | HuggingFace cache | ✅ (downloaded on first run) |

**Python packages (pip):**
```
anthropic
transformers
accelerate
torch
pdfplumber
chess
requests
```

---

## 13. KNOWN ISSUES & GOTCHAS

1. **ADB PATH** — must refresh PATH in each new PowerShell session:
   ```powershell
   $env:PATH = [System.Environment]::GetEnvironmentVariable("PATH", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("PATH", "User")
   ```

2. **ANTHROPIC_API_KEY in PowerShell** — new terminals don't inherit it automatically:
   ```powershell
   $env:ANTHROPIC_API_KEY = [System.Environment]::GetEnvironmentVariable("ANTHROPIC_API_KEY", "User")
   ```

3. **stc_pdf.py has wrong vault paths** — `gjet_mappe()` in stc_pdf.py still uses old paths (missing `Studie/` prefix). Needs same fix as stc_lyd.py. The correct pattern is:
   ```python
   _STUDIE  = VAULT / "Studie"
   _MEDISIN = _STUDIE / "Medisin"
   ```

4. **Tablet vault sync** — currently manual via `adb push`. Syncthing needs to be set up on tablet to automate this.

5. **NB-Whisper first-run** — downloads ~1.5 GB model on first run. Normal.

6. **KMP_DUPLICATE_LIB_OK=TRUE** — required for PyTorch on Windows. Already set in start_ciel.vbs and stc_lyd.py.

---

## 14. LINKEDIN / CV PRESENTATION

When phases 1-3 are running:

> An ambient AI assistant where the assistant is the interface — a breathing orb replaces the home screen. You write or speak to it, and whole workflows rise up: write 'lecture' and it records, transcribes, and takes structured notes. Privacy-first by design: a Python/FastAPI brain handles the heavy lifting; thin Flutter clients stay fast. Speech-to-text runs locally, data stays on-device, and every action runs through a fixed, audited command set.
> Tech: Python, FastAPI, Flutter, NB-Whisper, SQLite, Claude API.

**Important:** Say "custom Android launcher" not "OS" to technical audiences. "Ciel OS" is the brand name — valid and accurate for LinkedIn and non-technical contexts.

---

## 15. QUICK REFERENCE — FILE PATHS

```
Code (source of truth):    C:\Users\Karthik\.claude\
Code (git repo):           C:\Users\Karthik\ciel\
GitHub:                    https://github.com/Katchii-t4t/Ciel-OS (private)
Vault:                     C:\Users\Karthik\OneDrive\Obidian stasj\Katchi's stash\
Tablet vault (local copy): /sdcard/Documents/Katchi's stash/
Autostart:                 shell:startup → start_ciel.vbs
Python:                    C:\Users\Karthik\anaconda3\python.exe
```

---

*This handout was generated at the end of the session where the tablet arrived and basic setup was completed. The next session should start with Syncthing + Flutter verification, then immediately move to Phase 1 (FastAPI backend).*
