"""
Ciel-server — Fase 1 (Module A + B)
===================================
FastAPI-backend som pakkar inn dei eksisterande Ciel-agentane (stc_agent.py)
og eksponerer dei for tynne klientar (nettbrett/telefon) over HTTP + WebSocket.

PC = hjernen. Klientane renderer berre. All AI-inferens skjer her.

API-kontrakt (frå SPEC.md §9 / Module A):
  GET  /                     → status/info
  GET  /health              → helsesjekk
  POST /api/ask             → spør Ciel (REST, heile svaret)
  POST /api/transcribe      → lyd → tekst (NB-Whisper, Fase 3)
  GET  /api/vault/notes     → siste notat i vaulten
  GET  /api/vault/note      → eitt notat sitt innhald
  POST /api/command         → køyr ein kommando frå fast allow-liste
  GET  /api/state           → gjeldande modus + status
  GET  /api/tracker/today   → dagsscore (Fase 5, stub no)
  WS   /ws/stream           → token-for-token typewriter-svar
  WS   /ws/events           → push-hendingar (modusbyte, nye notat ...)

Tryggleik (SPEC.md §11):
  • ANTHROPIC_API_KEY berre frå miljøvariabel — aldri hardkoda. Klientane
    snakkar ALDRI direkte med Anthropic; berre denne serveren gjer det.
  • /api/command køyrer berre handlingar frå ei fast, versjonert allow-liste.
    Ingen "køyr vilkårleg streng"-handling finst. Kvar kommando vert logga.
  • Innhald er data, aldri kommandoar.

Køyr:  python ciel_server.py
       (eller: uvicorn ciel_server:app --host 0.0.0.0 --port 8765)
"""

import os, re, json, time, asyncio
from datetime import date, datetime, timezone
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# ── Gjenbruk den verkelege agent-logikken ────────────────────────────────────
# stc_agent er gjort importerbar (lazy klient + main()-guard), så vi arvar
# vault-deteksjon, vault-søk og kjelde-henting direkte — éin sanningskjelde.
import stc_agent as ciel
from stc_agent import (
    VAULT, STOPORD, IGNORE, PREFIXES,
    search_vault, get_critical, hits_to_ctx,
    fetch_snl, fetch_wikipedia, fetch_pubmed,
)

# ── Konfigurasjon ─────────────────────────────────────────────────────────────
PORT = int(os.environ.get("CIEL_PORT", "8765"))

# Smart LLM-routing (SPEC Module A): billegaste modell som klarar jobben.
# Overstyrbar med miljøvariablar.
MODEL_SIMPLE   = os.environ.get("CIEL_MODEL_SIMPLE",   "claude-haiku-4-5")
MODEL_COMPLEX  = os.environ.get("CIEL_MODEL_COMPLEX",  "claude-sonnet-4-6")
MODEL_CRITICAL = os.environ.get("CIEL_MODEL_CRITICAL", "claude-opus-4-8")
WHISPER_MODEL  = os.environ.get("CIEL_WHISPER", "NbAiLab/nb-whisper-medium")

# Modusar (SPEC §7) + heim-fargane (§6.3)
MODES = {
    "ambient":   {"colour": "#EF9F27", "meaning": "Standard / idle — gull"},
    "solo":      {"colour": "#85B7EB", "meaning": "Aleine — JARVIS-aktiv"},
    "social":    {"colour": "#97C459", "meaning": "Folk nær — stille"},
    "lecture":   {"colour": "#AFA9EC", "meaning": "Forelesing/LSB — opptak"},
    "wind-down": {"colour": "#F09595", "meaning": "Kveld — kvile"},
}

# Action-logg (SPEC §11: kvar kommando vert logga)
LOG_DIR = Path(__file__).resolve().parent / "logs"
LOG_DIR.mkdir(exist_ok=True)
ACTION_LOG = LOG_DIR / "action_log.jsonl"

# In-memory state
STATE = {
    "mode": "ambient",
    "girl_mode": False,
    "since": datetime.now(timezone.utc).isoformat(),
    "online": True,
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _log_action(kind: str, payload: dict):
    try:
        with ACTION_LOG.open("a", encoding="utf-8") as f:
            f.write(json.dumps({"ts": _now(), "kind": kind, "payload": payload},
                               ensure_ascii=False) + "\n")
    except Exception:
        pass


# ── Tema-klassifisering (girl mode auto-trigger, §6.6) ───────────────────────
GIRL_TRIGGERS = {
    "østrogen", "estrogen", "estradiol", "hrt", "hormon", "hormone",
    "progesteron", "mensen", "menstru", "sminke", "makeup", "kjole",
    "skjørt", "shopping", "feminin", "feminine", "bryst", "jenteprat",
    "transisjon", "transition", "antiandrogen",
}


def classify_girl_mode(question: str) -> bool:
    q = question.lower()
    return any(t in q for t in GIRL_TRIGGERS)


# ── LLM-routing ───────────────────────────────────────────────────────────────
def route_model(deep: bool, override: str | None = None) -> str:
    """Vel billegaste modell som passar oppgåva."""
    if override:
        return override
    return MODEL_COMPLEX if deep else MODEL_SIMPLE


# ── Prompt-bygging (speglar handle_stc / handle_A i stc_agent) ────────────────
def _terms(question: str) -> list[str]:
    return [w for w in re.findall(r"\b\w{4,}\b", question.lower()) if w not in STOPORD]


def build_general_prompt(question: str, note_context: str = "") -> str:
    """Generelt vault-svar — speglar handle_stc."""
    vault_ctx = hits_to_ctx(search_vault(_terms(question)))
    critical  = get_critical()
    dette = (f"\nDETTE NOTATET (det Katchi skreiv — bruk som primærkjelde):\n"
             f"{note_context}\n") if note_context else ""
    return f"""You are Ciel, the knowledge assistant for Dr. Katchi (she/her), a medicine + mathematics student at UiO. Speak calm, precise English (JARVIS-like). Her notes may be written in Norwegian Nynorsk — read them perfectly well, but ALWAYS answer in English.

IDENTITY:
{critical}
{dette}
RELEVANT NOTES FROM THE VAULT:
{vault_ctx}

QUESTION: {question}

- Prioritise THIS NOTE as the primary source; reference the source note when you use it.
- Clearly state any knowledge gaps if something is missing.
- Max 300 words, English, no markdown headers."""


def build_deep_prompt(question: str, note_context: str = "") -> str:
    """A+ djupdykk med SNL + Wikipedia + PubMed — speglar handle_A."""
    terms     = _terms(question)
    main_term = terms[0] if terms else question
    search_q  = " ".join(terms[:4]) if terms else question

    vault_ctx  = hits_to_ctx(search_vault(terms, top_n=4))
    snl_ctx    = fetch_snl(main_term) or ""
    wiki_ctx   = fetch_wikipedia(main_term) or fetch_wikipedia(question) or ""
    pubmed_ctx = fetch_pubmed(search_q)

    kjelder = []
    if snl_ctx:    kjelder.append(f"**SNL:**\n{snl_ctx}")
    if wiki_ctx:   kjelder.append(f"**Wikipedia:**\n{wiki_ctx}")
    if pubmed_ctx: kjelder.append(f"**PubMed:**\n{pubmed_ctx}")
    kjelder_tekst = "\n\n---\n\n".join(kjelder) if kjelder else "Ingen eksterne kjelder funne."

    dette = note_context if note_context else "(ingen notatkontekst frå klienten)"
    return f"""You are a professor of medicine answering a hard "A+ question" for Dr. Katchi (UiO). Answer in English even if the notes/sources are in Norwegian.

QUESTION: {question}

KATCHI'S NOTES (primary source):
{dette}

OTHER VAULT NOTES:
{vault_ctx}

ACADEMIC SOURCES (SNL / Wikipedia / PubMed):
{kjelder_tekst}

Give a precise, academic answer suited to a medicine student (UiO):

**Answer:** [Direct, precise answer — 2-4 sentences]

**Mechanism:** [The underlying biological/physiological mechanism]

**Clinical relevance:** [Why this matters clinically]

**Sources:** [Which source(s) support the answer]

Use proper terminology. LaTeX ($...$) for formulas if relevant. Max 350 words, English."""


def build_prompt(question: str, deep: bool, note_context: str = "") -> str:
    return build_deep_prompt(question, note_context) if deep else build_general_prompt(question, note_context)


# ── LLM-kall ──────────────────────────────────────────────────────────────────
def complete(prompt: str, model: str, max_tokens: int) -> str:
    """Blokkerande heilt-svar (køyrast i tråd frå async-kontekst)."""
    resp = ciel._get_client().messages.create(
        model=model, max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}],
    )
    return "".join(block.text for block in resp.content if getattr(block, "type", "") == "text")


async def astream_tokens(prompt: str, model: str, max_tokens: int):
    """Async generator som gir tokens. Køyrer den blokkerande SDK-streamen
    i ein tråd og dyttar tokens over ein asyncio.Queue."""
    loop = asyncio.get_running_loop()
    queue: asyncio.Queue = asyncio.Queue()
    SENTINEL = object()

    def worker():
        try:
            with ciel._get_client().messages.stream(
                model=model, max_tokens=max_tokens,
                messages=[{"role": "user", "content": prompt}],
            ) as stream:
                for text in stream.text_stream:
                    loop.call_soon_threadsafe(queue.put_nowait, text)
        except Exception as e:
            loop.call_soon_threadsafe(queue.put_nowait, {"__error__": str(e)})
        finally:
            loop.call_soon_threadsafe(queue.put_nowait, SENTINEL)

    loop.run_in_executor(None, worker)
    while True:
        item = await queue.get()
        if item is SENTINEL:
            break
        yield item


# ── Vault-hjelparar ───────────────────────────────────────────────────────────
def _safe_vault_path(rel: str) -> Path:
    """Hindrar path-traversal: sikrar at stien ligg inni vaulten."""
    p = (VAULT / rel).resolve()
    root = VAULT.resolve()
    if p != root and root not in p.parents:
        raise HTTPException(400, "Sti utanfor vaulten.")
    if not p.exists():
        raise HTTPException(404, f"Notat ikkje funne: {rel}")
    return p


def list_notes(limit: int = 30):
    notes = []
    for path in VAULT.rglob("*.md"):
        if any(d in path.parts for d in IGNORE):
            continue
        if path.name.startswith("_"):
            continue
        try:
            st = path.stat()
        except Exception:
            continue
        notes.append((st.st_mtime, path))
    notes.sort(reverse=True)
    out = []
    for mtime, path in notes[:limit]:
        try:
            snippet = path.read_text(encoding="utf-8", errors="ignore")[:200].strip()
        except Exception:
            snippet = ""
        out.append({
            "name": path.stem,
            "path": str(path.relative_to(VAULT)).replace("\\", "/"),
            "modified": datetime.fromtimestamp(mtime, timezone.utc).isoformat(),
            "snippet": snippet,
        })
    return out


# ── Hendings-hub (WS /ws/events) ──────────────────────────────────────────────
class EventHub:
    def __init__(self):
        self.clients: set[WebSocket] = set()

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.clients.add(ws)

    def disconnect(self, ws: WebSocket):
        self.clients.discard(ws)

    async def broadcast(self, event: dict):
        dead = []
        for ws in list(self.clients):
            try:
                await ws.send_json(event)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)


hub = EventHub()


async def _maybe_girl_mode(question: str):
    """Auto girl mode (§6.6): glir til trans-flagg på feminine/personlege tema,
    og tilbake til gull elles. Sender overgang til orben via /ws/events."""
    gm = classify_girl_mode(question)
    if gm != STATE["girl_mode"]:
        STATE["girl_mode"] = gm
        await hub.broadcast({"type": "girl_mode", "on": gm, "ts": _now()})


# ── Kommando-eksekutor (fast allow-liste, SPEC §11) ──────────────────────────
async def exec_command(name: str, args: dict) -> dict:
    """Køyrer berre handlingar frå allow-lista. Ingen vilkårleg eksekvering."""
    if name == "set_mode":
        mode = (args.get("mode") or "").lower()
        if mode not in MODES:
            raise HTTPException(400, f"Ukjend modus: {mode}. Gyldige: {list(MODES)}")
        STATE["mode"] = mode
        STATE["since"] = _now()
        await hub.broadcast({"type": "mode", "mode": mode, "colour": MODES[mode]["colour"], "ts": _now()})
        return {"mode": mode, "colour": MODES[mode]["colour"]}

    if name == "set_girl_mode":
        on = bool(args.get("on", True))
        STATE["girl_mode"] = on
        await hub.broadcast({"type": "girl_mode", "on": on, "ts": _now()})
        return {"girl_mode": on}

    if name == "open_note":
        rel = args.get("path") or args.get("name")
        if not rel:
            raise HTTPException(400, "open_note krev 'path'.")
        if not rel.endswith(".md"):
            rel += ".md"
        p = _safe_vault_path(rel)
        content = p.read_text(encoding="utf-8", errors="ignore")
        return {"path": rel, "content": content}

    if name == "search_vault":
        query = args.get("query", "")
        hits = search_vault(_terms(query))
        return {"hits": [{"name": stem, "score": score, "snippet": txt} for score, stem, txt in hits]}

    raise HTTPException(400, f"Kommando ikkje i allow-lista: {name}")


ALLOWED_COMMANDS = {"set_mode", "set_girl_mode", "open_note", "search_vault"}


# ── FastAPI-app ───────────────────────────────────────────────────────────────
app = FastAPI(title="Ciel Server", version="1.0.0")

# CORS — LAN/Tailscale. v1: tillat alt (lukka nett); stram inn seinare ved behov.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


class AskRequest(BaseModel):
    question: str
    deep: bool = False
    context: str = ""        # valfri notatkontekst frå klienten
    model: str | None = None  # valfri overstyring av modell


class CommandRequest(BaseModel):
    command: str
    args: dict = {}


@app.get("/")
def root():
    return {
        "name": "Ciel Server",
        "version": "1.0.0",
        "vault": VAULT.name,
        "mode": STATE["mode"],
        "models": {"simple": MODEL_SIMPLE, "complex": MODEL_COMPLEX, "critical": MODEL_CRITICAL},
        "key_set": bool(os.environ.get("ANTHROPIC_API_KEY")),
    }


@app.get("/health")
def health():
    return {"ok": True, "ts": _now()}


@app.get("/api/state")
def get_state():
    m = STATE["mode"]
    return {**STATE, "colour": MODES[m]["colour"], "meaning": MODES[m]["meaning"], "modes": MODES}


@app.get("/api/vault/notes")
def vault_notes(limit: int = 30):
    return {"notes": list_notes(limit)}


@app.get("/api/vault/note")
def vault_note(path: str):
    p = _safe_vault_path(path if path.endswith(".md") else path + ".md")
    return {"path": path, "content": p.read_text(encoding="utf-8", errors="ignore")}


@app.get("/api/tracker/today")
def tracker_today():
    # Stub — full tracker kjem i Fase 5 (Module J). Velvære-vakt: kvile er positivt.
    return {
        "date": date.today().isoformat(),
        "score": None,
        "priority": "Livssporing kjem i Fase 5 (Module J).",
        "metrics": {},
        "wellbeing_note": "Kvile er ein positiv metrikk — ingen restriksjons-rammar.",
    }


@app.post("/api/ask")
async def api_ask(req: AskRequest):
    if not req.question.strip():
        raise HTTPException(400, "Tomt spørsmål.")
    model = route_model(req.deep, req.model)
    max_tokens = 1200 if req.deep else 900
    _log_action("ask", {"deep": req.deep, "model": model, "q": req.question[:200]})
    await _maybe_girl_mode(req.question)
    # Bygg prompt (kan gjere nett-I/O) + LLM-kall i tråd, så event-loopen ikkje blokkerer.
    prompt = await asyncio.to_thread(build_prompt, req.question, req.deep, req.context)
    try:
        answer = await asyncio.to_thread(complete, prompt, model, max_tokens)
    except Exception as e:
        raise HTTPException(502, f"LLM-feil: {e}")
    return {"answer": answer, "model": model, "deep": req.deep}


@app.post("/api/command")
async def api_command(req: CommandRequest):
    if req.command not in ALLOWED_COMMANDS:
        raise HTTPException(400, f"Kommando ikkje i allow-lista: {req.command}")
    _log_action("command", {"command": req.command, "args": req.args})
    result = await exec_command(req.command, req.args)
    return {"ok": True, "command": req.command, "result": result}


_whisper = None


def _get_whisper():
    """Lazy-last NB-Whisper (norsk, frå Nasjonalbiblioteket). Berre éin gong."""
    global _whisper
    if _whisper is None:
        import torch
        from transformers import pipeline as hf_pipeline
        _whisper = hf_pipeline(
            "automatic-speech-recognition",
            model=WHISPER_MODEL,
            device="cpu",
            torch_dtype=torch.float32,
        )
    return _whisper


@app.post("/api/transcribe")
async def api_transcribe(file: UploadFile = File(...)):
    """Lyd (WAV) → tekst via NB-Whisper på PC-en. Tvungen norsk."""
    try:
        import soundfile  # noqa: F401
    except ImportError:
        raise HTTPException(503, "STT krev torch + transformers + soundfile på PC-en.")
    data = await file.read()
    if not data:
        raise HTTPException(400, "Tom lydfil.")

    def work():
        import io as _io
        import soundfile as _sf
        arr, sr = _sf.read(_io.BytesIO(data), dtype="float32")
        if getattr(arr, "ndim", 1) > 1:
            arr = arr.mean(axis=1)  # til mono
        pipe = _get_whisper()
        res = pipe(
            {"array": arr, "sampling_rate": int(sr)},
            chunk_length_s=30,
            batch_size=4,
            return_timestamps=False,
            generate_kwargs={"language": "no", "task": "transcribe"},
        )
        return (res.get("text") or "").strip()

    try:
        text = await asyncio.to_thread(work)
    except Exception as e:
        raise HTTPException(502, f"Transkriberingsfeil: {e}")
    _log_action("transcribe", {"chars": len(text)})
    return {"text": text}


@app.websocket("/ws/stream")
async def ws_stream(ws: WebSocket):
    """Token-for-token typewriter. Klient sender JSON:
    {"question": "...", "deep": false, "context": "...", "model": null}
    Server sender {"token": "..."} per bit, så {"done": true, "model": ...}."""
    await ws.accept()
    try:
        while True:
            data = await ws.receive_json()
            question = (data.get("question") or "").strip()
            if not question:
                await ws.send_json({"error": "Tomt spørsmål."})
                continue
            deep    = bool(data.get("deep", False))
            context = data.get("context", "")
            model   = route_model(deep, data.get("model"))
            max_tokens = 1200 if deep else 900
            _log_action("ws_ask", {"deep": deep, "model": model, "q": question[:200]})
            await _maybe_girl_mode(question)

            await ws.send_json({"start": True, "model": model, "deep": deep})
            prompt = await asyncio.to_thread(build_prompt, question, deep, context)

            async for item in astream_tokens(prompt, model, max_tokens):
                if isinstance(item, dict) and "__error__" in item:
                    await ws.send_json({"error": item["__error__"]})
                    break
                await ws.send_json({"token": item})
            await ws.send_json({"done": True, "model": model})
    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await ws.send_json({"error": str(e)})
        except Exception:
            pass


@app.websocket("/ws/events")
async def ws_events(ws: WebSocket):
    """Push-kanal: modusbyte, girl-mode, m.m. Sender straks gjeldande state."""
    await hub.connect(ws)
    try:
        m = STATE["mode"]
        await ws.send_json({"type": "state", **STATE, "colour": MODES[m]["colour"], "ts": _now()})
        while True:
            # Hald tilkoplinga open; klienten treng ikkje sende noko.
            await asyncio.sleep(30)
            await ws.send_json({"type": "ping", "ts": _now()})
    except WebSocketDisconnect:
        hub.disconnect(ws)
    except Exception:
        hub.disconnect(ws)


if __name__ == "__main__":
    import uvicorn
    print(f"Ciel-server startar på http://0.0.0.0:{PORT}")
    print(f"Vault: {VAULT}")
    print(f"API-nøkkel sett: {bool(os.environ.get('ANTHROPIC_API_KEY'))}")
    uvicorn.run(app, host="0.0.0.0", port=PORT)
