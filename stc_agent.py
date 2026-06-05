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

# UTF-8 output
os.environ.setdefault("PYTHONIOENCODING", "utf-8")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ── Konfigurasjon ──────────────────────────────────────────────────────────────
# Vault-deteksjon — portabel (fungerer på alle maskiner, uavhengig av brukarnamn).
# Overstyr med miljøvariabelen CIEL_VAULT (peikar rett på vault-rota) om du vil.
_env_vault = os.environ.get("CIEL_VAULT")
if _env_vault:
    VAULT = Path(_env_vault)
    if not VAULT.is_dir():
        print(f"FEIL: CIEL_VAULT peikar ikkje på ei mappe: {VAULT}"); raise SystemExit(1)
else:
    _home   = Path(os.environ.get("USERPROFILE") or Path.home())
    _parent = _home / "OneDrive" / "Obidian stasj"
    _match  = ([d for d in _parent.iterdir() if "stash" in d.name.lower() and "Copy" not in d.name]
               if _parent.is_dir() else [])
    if not _match:
        print(f"FEIL: Fann ikkje vault-mappa under {_parent}!"); raise SystemExit(1)
    VAULT = _match[0]
MODEL        = "claude-haiku-4-5"
POLL_SECS    = 3
STREAM_CHUNK = 12   # Skriv til fil kvar N teikn → skrivemaskin-effekt

IGNORE  = {"Usikkere notat ord", ".obsidian", ".trash"}
STOPORD = {"kva","kan","om","er","og","til","frå","fra","med","som","det","dei",
           "har","for","veit","meg","seg","kven","korleis","ein","eit","den",
           "ikkje","enn","men","hva","hvordan","ikke","deg","jeg","min","din"}

# Rekkjefølgje avgjer matching — lengre prefiks MUST kome fyrst
PREFIXES = ["Ciel-sjekk:", "Ciel-diagram:", "Ciel-skriv:", "Ciel-kryssref:",
            "Ciel-latex:", "Ciel-eksamen:", "Ciel-forslag:", "Ciel-A:",
            "Ciel-chess-W:", "Ciel-chess-B:", "Ciel-chess:", "Ciel:"]

CHESS_PREFIXES = {"Ciel-chess:", "Ciel-chess-W:", "Ciel-chess-B:"}

CHESS_DIR = VAULT / "Extracurricular" / "Chess"

# ── Sjakk-hjelparar ───────────────────────────────────────────────────────────
# Figurnotasjon (som i sjakkbøker) — ♗xh7 istadenfor Bxh7
FAN_MAP  = {'K': '♔', 'Q': '♕', 'R': '♖', 'B': '♗', 'N': '♘'}

def to_fan(san: str) -> str:
    """Konverter SAN til figurnotasjon (♗, ♘, ♕, ♖, ♔)."""
    if san and san[0] in FAN_MAP:
        return FAN_MAP[san[0]] + san[1:]
    return san

# Materialverdiar for balansekart
PIECE_VAL = {chess.PAWN: 1, chess.KNIGHT: 3, chess.BISHOP: 3,
             chess.ROOK: 5, chess.QUEEN: 9}

def mat_score(board: chess.Board) -> int:
    """Materialbalanse: positiv = kvit fordel."""
    s = 0
    for pt, val in PIECE_VAL.items():
        s += val * len(board.pieces(pt, chess.WHITE))
        s -= val * len(board.pieces(pt, chess.BLACK))
    return s

# Klassiske Lichess-brune brett-fargar (som i sjakkbøker og -sider)
BOARD_COLORS = {
    "square light": "#F0D9B5",   # varm krem
    "square dark":  "#B58863",   # varm brun
    "margin":       "#2C1810",   # mørk tre-kant
    "coord":        "#E8D5B0",   # lyse koordinatar i kanten
}

# Lazy klient — vert berre oppretta når vi faktisk treng API-et.
# Slik kan modulen importerast (t.d. av ciel_server.py) utan at nøkkelen finst enno.
_client = None

def _get_client():
    global _client
    if _client is None:
        if not os.environ.get("ANTHROPIC_API_KEY"):
            raise RuntimeError("ANTHROPIC_API_KEY er ikkje sett!")
        _client = anthropic.Anthropic()
    return _client


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

def get_current_note_ctx(pre: list) -> str:
    """
    Returnerer innhaldet i gjeldande notat OVER Ciel:-linja (maks 4000 teikn).
    Filterer vekk tidlegare Ciel-svar så Claude ikkje les sine eigne tidlegare svar.
    """
    # pre[-1] er sjølve Ciel:-linja — ekskluder den
    linjer = pre[:-1]

    # Filtrer vekk tidlegare **Svar (Ciel...)-blokkar
    reinskt = []
    i_svar  = False
    for linje in linjer:
        s = linje.strip()
        if s.startswith("**Svar ("):
            i_svar = True
        if not i_svar:
            reinskt.append(linje)
        # Svar-blokken er over når vi møter ei linje som ser ut som brukarinnhald
        # (ikkje-tom, ikkje ein sitat, ikkje cursor)
        if i_svar and s and not s.startswith((">", "▊", "**Svar", "---")):
            # Sjekk at vi ikkje er midt i svaret
            # Enkelt heuristikk: sett i_svar = False på neste ikkje-Ciel linje
            if not any(s.startswith(p) for p in PREFIXES):
                i_svar = False
                reinskt.append(linje)

    tekst = "\n".join(reinskt).strip()
    # Ta dei siste 4000 teikna (mest relevante konteksten = rett over spørsmålet)
    return tekst[-4000:] if len(tekst) > 4000 else tekst


# ── PDF-embedding i notat ────────────────────────────────────────────────────
def _finn_pdf(filnamn: str):
    """Finn PDF i vaulten basert på filnamn (søker rekursivt)."""
    for path in VAULT.rglob("*.pdf"):
        if path.name.lower() == filnamn.lower():
            return path
    return None

def _les_pdf_tekst(path, maks_teikn: int = 8000) -> str:
    """Trekk ut tekst frå PDF med pdfplumber."""
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

def hent_pdf_kontekst(linjer: list) -> str:
    """
    Finn alle ![[*.pdf]]-embeds i ei liste med linjer og
    returnerer den samanslåtte teksten frå alle PDFane.
    Brukt automatisk av alle Ciel:-handterar.
    """
    delar = []
    sett  = set()
    for linje in linjer:
        for filnamn in re.findall(r'!\[\[([^\]]+\.pdf)\]\]', linje, re.IGNORECASE):
            if filnamn in sett:
                continue
            sett.add(filnamn)
            pdf_path = _finn_pdf(filnamn)
            if pdf_path:
                print(f"  [pdf-embed] Les: {filnamn}...")
                tekst = _les_pdf_tekst(pdf_path)
                delar.append(f"=== PDF: {filnamn} ===\n{tekst}")
            else:
                print(f"  [pdf-embed] Ikkje funne: {filnamn}")
    return "\n\n".join(delar)


# ── Web-kjelder ───────────────────────────────────────────────────────────────
def fetch_snl(term):
    """Hent artikkel frå Store Norske Leksikon."""
    try:
        r = requests.get(
            "https://snl.no/api/v1/search",
            params={"query": term, "limit": 1},
            timeout=5
        )
        results = r.json()
        if not results:
            return None
        headword    = results[0].get("headword", term)
        article_url = results[0].get("article_url_json")
        if not article_url:
            return None
        article = requests.get(article_url, timeout=5).json()
        body    = re.sub(r"<[^>]+>", " ", article.get("body", ""))
        body    = re.sub(r"\s+", " ", body).strip()[:1200]
        if body:
            return f"SNL — {headword}:\n{body}"
    except Exception:
        pass
    return None

def fetch_wikipedia(term):
    """Hent samandrag frå norsk (eller engelsk) Wikipedia."""
    for lang in ("no", "en"):
        try:
            r = requests.get(
                f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{term.replace(' ', '_')}",
                timeout=5
            )
            if r.status_code == 200:
                extract = r.json().get("extract", "")
                if extract:
                    return f"Wikipedia ({lang}) — {term}:\n{extract[:1200]}"
        except Exception:
            pass
    return None


def fetch_pubmed(query: str) -> str:
    """Hent topp 3 abstrakt frå PubMed. Gratis, ingen API-nøkkel nødvendig."""
    try:
        # Steg 1: søk etter relevante artiklar
        search = requests.get(
            "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi",
            params={"db": "pubmed", "term": query, "retmax": 3,
                    "retmode": "json", "sort": "relevance"},
            timeout=8
        )
        ids = search.json().get("esearchresult", {}).get("idlist", [])
        if not ids:
            return ""

        # Steg 2: hent abstrakt
        fetch = requests.get(
            "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi",
            params={"db": "pubmed", "id": ",".join(ids),
                    "rettype": "abstract", "retmode": "text"},
            timeout=10
        )
        return f"PubMed ({len(ids)} artiklar):\n{fetch.text[:2500]}"
    except Exception:
        return ""


# ── Streaming til fil (skrivemaskin-effekt) ───────────────────────────────────
def stream_to_file(filepath, pre_lines, post_lines, header, prompt, max_tokens=900):
    """
    Streamer API-svar direkte til fila i små bitar.
    Obsidian viser bokstav-for-bokstav-effekt i sanntid.
    """
    full_text    = ""
    chunk_buffer = ""

    def write_current(cursor=True):
        suffix = ["▊"] if cursor else []
        lines  = [header] + full_text.split("\n") + suffix + [""]
        filepath.write_text(
            "\n".join(pre_lines + lines + post_lines),
            encoding="utf-8"
        )

    write_current(cursor=True)  # Vis cursor med ein gong

    try:
        with _get_client().messages.stream(
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

    write_current(cursor=False)  # Endeleg versjon utan cursor
    return full_text


# ── Handlarar per prefiks ─────────────────────────────────────────────────────
def handle_stc(q, filepath, pre, post, header):
    """Svar frå vaulten — les notata I same fil + eventuelle ![[*.pdf]]-embeds."""
    terms      = [w for w in re.findall(r"\b\w{4,}\b", q.lower()) if w not in STOPORD]
    ctx        = hits_to_ctx(search_vault(terms, exclude_path=filepath))
    critical   = get_critical()
    notat_ctx  = get_current_note_ctx(pre)   # ← innhald over Ciel:-linja i same fil

    # Les PDFar som er embeda i notatet (t.d. ![[forelesning.pdf]])
    pdf_ctx = hent_pdf_kontekst(pre + post)
    pdf_seksjon = f"""
PDF-VEDLEGG I DETTE NOTATET:
{pdf_ctx}

""" if pdf_ctx else ""

    dette_notatet = f"""
DETTE NOTATET (det Katchi skreiv over spørsmålet — bruk dette som primærkjelde):
{notat_ctx}

""" if notat_ctx else ""

    prompt = f"""Du er kunnskapsassistenten til Katchi (ho/hennar), medisinstudent UiO.
{f"Du har tilgang til {len(pdf_ctx.split('=== PDF:')) - 1} PDF-vedlegg lasta opp i notatet — prioriter desse som hovudkjelde." if pdf_ctx else ""}

IDENTITET:
{critical}
{dette_notatet}{pdf_seksjon}RELEVANTE NOTAT FRÅ VAULTEN:
{ctx}

SPOERSMAAL: {q}

- Prioriter innhaldet i DETTE NOTATET og PDF-vedlegg som primærkjelder
- Referer til PDF-tittel eller kjeldenotat når du bruker informasjon derifrå
- Sei tydeleg kva som er kunnskapsgap viss noko manglar
- Maks 300 ord, paa nynorsk, ingen markdown-overskrifter"""
    stream_to_file(filepath, pre, post, header, prompt)


def handle_sjekk(q, filepath, pre, post, header):
    """Faktasjekk mot SNL + Wikipedia, les notata i same fil + PDF-embeds."""
    terms      = [w for w in re.findall(r"\b\w{4,}\b", q.lower()) if w not in STOPORD]
    vault_ctx  = hits_to_ctx(search_vault(terms, exclude_path=filepath))
    notat_ctx  = get_current_note_ctx(pre)
    main_term  = terms[0] if terms else q
    web_ctx    = fetch_snl(main_term) or fetch_wikipedia(main_term) or fetch_wikipedia(q) \
                 or "Fann ingen relevante kjelder på nett."
    pdf_ctx    = hent_pdf_kontekst(pre + post)
    pdf_del    = f"\nPDF-VEDLEGG:\n{pdf_ctx}\n" if pdf_ctx else ""
    dette_del  = f"\nDETTE NOTATET:\n{notat_ctx}\n" if notat_ctx else ""
    prompt = f"""Du er faktasjekkar for Katchi (medisinstudent UiO).
{dette_del}
VAULT-NOTAT:
{vault_ctx}
{pdf_del}
EKSTERN KJELDE (SNL/Wikipedia):
{web_ctx}

OPPGÅVE: Samanlikn innhaldet (særleg frå DETTE NOTATET og vaulten) mot den eksterne kjelda for "{q}".
- Kva stemmer? Kva er feil eller unøyaktig? Kva viktig manglar?

Maks 200 ord, på nynorsk. Ver konkret — referer til spesifikke kjelder."""
    stream_to_file(filepath, pre, post, header, prompt)


def handle_diagram(q, filepath, pre, post, header):
    """Generer Mermaid-diagram. Obsidian rendrar det automatisk."""
    terms  = [w for w in re.findall(r"\b\w{4,}\b", q.lower()) if w not in STOPORD]
    ctx    = hits_to_ctx(search_vault(terms, exclude_path=filepath))
    prompt = f"""Lag eit Mermaid-diagram basert på desse notatane om "{q}":

{ctx}

Vel passande type (flowchart TD, sequenceDiagram, eller mindmap).
Bruk BERRE informasjon frå notatane ovanfor.
Returner KUN kode-blokken — ingen tekst utanfor:

```mermaid
[diagrammet her]
```"""
    stream_to_file(filepath, pre, post, header, prompt)


def handle_skriv(q, filepath, pre, post, header):
    """Omskrive og rettskrive tekst på nynorsk."""
    prompt = f"""Du er nynorsk-korrekturlesar og omskrivar.

TEKST: {q}

Oppgåve:
1. Rett opp stavefeil og grammatikk
2. Gjer teksten meir flytande og presis
3. Bruk korrekt nynorsk
4. Behald fagleg innhald og presisjon

Returner BERRE den omskrivne teksten, utan kommentar eller forklaring."""
    stream_to_file(filepath, pre, post, header, prompt)


def handle_kryssref(q, filepath, pre, post, header):
    """Finn motstridande informasjon mellom notat i vaulten."""
    terms = [w for w in re.findall(r"\b\w{4,}\b", q.lower()) if w not in STOPORD]
    hits  = search_vault(terms, exclude_path=filepath, top_n=8)
    ctx   = hits_to_ctx(hits)
    prompt = f"""Analyser om desse notatane er innbyrdes konsistente om "{q}":

{ctx}

Oppgåve:
- Finn motstridande påstandar mellom notat
- Finn overlappande innhald som bør samlast i eitt notat
- Peik på kva som bør oppdaterast eller verifiserast
- Viss alt er konsistent: sei det tydeleg

Maks 250 ord, på nynorsk. Referer til spesifikke notatnamn."""
    stream_to_file(filepath, pre, post, header, prompt)


def handle_latex(q, filepath, pre, post, header):
    """Forklar med LaTeX-matematikk. Obsidian rendrar $...$ og $$...$$ automatisk."""
    terms  = [w for w in re.findall(r"\b\w{4,}\b", q.lower()) if w not in STOPORD]
    ctx    = hits_to_ctx(search_vault(terms, exclude_path=filepath))
    prompt = f"""Du er matematikk- og naturvitskapslærar for Katchi (medisinstudent UiO).

RELEVANTE NOTAT:
{ctx}

SPØRSMÅL: {q}

Svar med korrekte LaTeX-formlar der det er relevant.
- Bruk $...$ for innlinjematematikk (t.d. $V_m = -70\\text{{ mV}}$)
- Bruk $$...$$ for sentrale formlar på eiga linje
- Forklar kvar formel i ord etterpå
- Maks 250 ord, på nynorsk
- Obsidian rendrar LaTeX automatisk, så bruk det gjerne"""
    stream_to_file(filepath, pre, post, header, prompt)


def handle_eksamen(q, filepath, pre, post, header):
    """Eksamensgap-analyse — samanliknar vaulten mot pensum for eit tema."""
    terms    = [w for w in re.findall(r"\b\w{4,}\b", q.lower()) if w not in STOPORD]
    hits     = search_vault(terms, exclude_path=filepath, top_n=10)
    vault_ctx = hits_to_ctx(hits)
    critical  = get_critical()

    # Prøv å hente pensum-notat
    pensum_ctx = ""
    for path in VAULT.rglob("*.md"):
        if any(x in path.name.lower() for x in ["pensum", "curriculum", "oversikt", "plan"]):
            try:
                pensum_ctx += f"\n### {path.stem}\n{path.read_text(encoding='utf-8', errors='ignore')[:600]}\n"
            except Exception:
                pass

    prompt = f"""Du er eksamensrettleiar for Katchi (medisinstudent UiO, {date.today().strftime('%Y')}).

IDENTITET:
{critical}

VAULT-INNHALD OM "{q}":
{vault_ctx}

PENSUM/OVERSIKTSNOTAT:
{pensum_ctx or "Ingen pensum-notat funne i vaulten."}

OPPGÅVE — lag ein eksamensanalyse for "{q}":

**Kva ho kan (frå vaulten):** [konkret liste]
**Kritiske gap for eksamen:** [kva manglar, rangert etter viktigheit]
**Tilrådd studieplan:** [3-5 konkrete steg]
**Vanskelege omgrep å øve på:** [spesifikke ting å repetere]

Maks 300 ord, på nynorsk. Ver direkte og konkret."""
    stream_to_file(filepath, pre, post, header, prompt)


def handle_forslag(q, filepath, pre, post, header):
    """Finn relaterte notat og foreslå kva som bør leggjast til / lenkas."""
    terms = [w for w in re.findall(r"\b\w{4,}\b", q.lower()) if w not in STOPORD]
    hits  = search_vault(terms, exclude_path=filepath, top_n=8)
    ctx   = hits_to_ctx(hits)

    # Les også innhaldet i gjeldande fil for kontekst
    try:
        current_content = filepath.read_text(encoding="utf-8", errors="ignore")[:800]
    except Exception:
        current_content = ""

    prompt = f"""Du er ein Obsidian-assistent som hjelper Katchi å byggje ut second brain sin.

GJELDANDE NOTAT ({filepath.stem}):
{current_content}

RELATERTE NOTAT I VAULTEN:
{ctx}

SPØRSMÅL/TEMA: {q}

Gi konkrete forslag:
1. **Notat å lenke til:** Kva [[wikilenker]] bør leggjast til i dette notatet?
2. **Innhald som manglar:** Kva bør leggjast til i dette notatet?
3. **Nye notat å opprette:** Kva notat burde eksistere men gjer det ikkje?
4. **Koplingar til andre spor:** Korleis heng dette saman med medisin/CogPrint/EPIC AI?

Maks 200 ord, på nynorsk. Ver konkret med notatnamn."""
    stream_to_file(filepath, pre, post, header, prompt)


def handle_A(q, filepath, pre, post, header):
    """
    A+ spørsmål frå LSB — djupdykk med SNL + Wikipedia + PubMed + vault.
    For dei vanskelege spørsmåla læraren stiller etter gjennomgang av pensum.
    """
    terms     = [w for w in re.findall(r"\b\w{4,}\b", q.lower()) if w not in STOPORD]
    main_term = terms[0] if terms else q
    search_q  = " ".join(terms[:4]) if terms else q

    print(f"  [Ciel-A] Søkjer: SNL + Wikipedia + PubMed for «{q[:60]}»...")

    vault_ctx  = hits_to_ctx(search_vault(terms, exclude_path=filepath, top_n=4))
    notat_ctx  = get_current_note_ctx(pre)
    snl_ctx    = fetch_snl(main_term) or (fetch_snl(" ".join(terms[:2])) if len(terms) > 1 else "") or ""
    wiki_ctx   = fetch_wikipedia(main_term) or fetch_wikipedia(q) or ""
    pubmed_ctx = fetch_pubmed(search_q)

    kjelder = []
    if snl_ctx:    kjelder.append(f"**SNL:**\n{snl_ctx}")
    if wiki_ctx:   kjelder.append(f"**Wikipedia:**\n{wiki_ctx}")
    if pubmed_ctx: kjelder.append(f"**PubMed:**\n{pubmed_ctx}")
    kjelder_tekst = "\n\n---\n\n".join(kjelder) if kjelder else "Ingen eksterne kjelder funne."

    print(f"  [Ciel-A] Kjelder: SNL={'ja' if snl_ctx else 'nei'} · "
          f"Wiki={'ja' if wiki_ctx else 'nei'} · "
          f"PubMed={'ja' if pubmed_ctx else 'nei'}")

    prompt = f"""Du er ein professor i medisin som svarar på eit vanskeleg "A+ spørsmål" stilt av ein LSB-lærar (lærarstyrt studiegruppetime) til medisinstudentar ved UiO.

SPØRSMÅL: {q}

KATCHI SINE NOTAT I DETTE DOKUMENTET (primærkjelde — det ho skreiv under LSB-timen):
{notat_ctx if notat_ctx else "(ingen notat funne over spørsmålet)"}

ANDRE VAULT-NOTAT:
{vault_ctx}

FAGLEGE KJELDER (SNL / Wikipedia / PubMed):
{kjelder_tekst}

Gi eit presist, akademisk svar eigna for ein medisinstudent (tidleg semester, UiO):

**Svar:** [Direkte, presis svar på spørsmålet — 2-4 setningar]

**Mekanisme:** [Den biologiske/kjemiske/fysiologiske mekanismen bak — ver konkret]

**Klinisk relevans:** [Kvifor er dette viktig i klinisk praksis?]

**Kjelder:** [Kva kilde(r) støttar svaret — SNL, Wikipedia, PubMed-tittel]

Bruk fagterminologi. LaTeX ($...$) for formlar viss relevant. Maks 350 ord, på nynorsk."""

    stream_to_file(filepath, pre, post, header, prompt, max_tokens=1200)


# ── Ciel-chess ────────────────────────────────────────────────────────────────
def handle_chess(q, filepath, pre, post, header, orientation=chess.WHITE):
    """
    Parser PGN frå chess.com. Genererer:
      - Partikort (spelarar, rating, opning, tidskontroll)
      - Materialbalanse-graf (Mermaid xychart)
      - SVG-brett per trekk med figurnotasjon + analyse under kvart brett
    """
    today   = date.today().strftime("%Y-%m-%d")
    img_dir = CHESS_DIR / "bilete" / today
    img_dir.mkdir(parents=True, exist_ok=True)

    # ── Parse trekkane ─────────────────────────────────────────────────────────
    board     = chess.Board()
    move_objs = []
    pgn_headers = {}

    try:
        game = chess.pgn.read_game(io.StringIO(q))
        if game:
            pgn_headers = dict(game.headers)
            for move in game.mainline_moves():
                move_objs.append(move)
                board.push(move)
        else:
            raise ValueError("Ikkje gyldig PGN")
    except Exception:
        # Fallback: handter "1. e4 e5 2. Nf3 ..." eller berre "e4 e5 Nf3"
        board = chess.Board()
        rå = re.sub(r'\d+\.\.\.', '', q)
        rå = re.sub(r'\d+\.', '', rå)
        rå = re.sub(r'\{[^}]*\}', '', rå)
        rå = re.sub(r'\$\d+', '', rå)
        for tok in rå.split():
            tok = tok.strip('!?+#')
            if not tok or tok in ('1-0','0-1','1/2-1/2','*'):
                continue
            try:
                m = board.parse_san(tok)
                move_objs.append(m)
                board.push(m)
            except Exception:
                pass

    if not move_objs:
        feil = [header, "Klarte ikkje parse trekka. Prøv: Del → Kopier PGN i chess.com.", ""]
        filepath.write_text("\n".join(pre + feil + post), encoding="utf-8")
        return

    # ── Trekk + materialbalanse per stilling ──────────────────────────────────
    board    = chess.Board()
    svg_refs = []   # (trekk_nr, san, fan, filnamn, mat_etter)
    mat_vals = [0]  # materialbalanse FØR trekk 1 (startposisjon = 0)

    for idx, move in enumerate(move_objs):
        san  = board.san(move)
        fan  = to_fan(san)
        board.push(move)
        mat_vals.append(mat_score(board))
        safe = san.replace('/','_').replace('+','plus').replace('#','matt')
        svg_txt = chess.svg.board(board, lastmove=move,
                                  orientation=orientation, size=360,
                                  colors=BOARD_COLORS)
        fname = f"trekk_{idx+1:03d}_{safe}.svg"
        (img_dir / fname).write_text(svg_txt, encoding="utf-8")
        svg_refs.append((idx + 1, san, fan, fname, mat_score(board)))

    print(f"  [chess] {len(svg_refs)} SVG-ar → {img_dir.relative_to(VAULT)}")

    # ── PGN-metadata ──────────────────────────────────────────────────────────
    white      = pgn_headers.get('White', '?')
    black      = pgn_headers.get('Black', '?')
    white_elo  = pgn_headers.get('WhiteElo', '—')
    black_elo  = pgn_headers.get('BlackElo', '—')
    result_raw = pgn_headers.get('Result', '*')
    opening    = pgn_headers.get('Opening', '')          # kan vere tom
    eco        = pgn_headers.get('ECO', '')
    time_ctrl  = pgn_headers.get('TimeControl', '—')
    game_date  = pgn_headers.get('Date', today).replace('.', '-')

    # Bygg "1. e4 e5 2. Nf3 Nc6 ..." for opningsdeteksjon (fyrste 8 trekk)
    _tb = chess.Board()
    _san8 = []
    for _mv in move_objs[:8]:
        _san8.append(_tb.san(_mv))
        _tb.push(_mv)
    opening_seq = " ".join(
        f"{i//2+1}. {_san8[i]}" + (f" {_san8[i+1]}" if i+1 < len(_san8) else "")
        for i in range(0, len(_san8), 2)
    )

    # Lesleg resultat
    if result_raw == '1-0':
        result_vis = f"**{white} vann** (1-0)"
        winner_side = 'Kvit'
    elif result_raw == '0-1':
        result_vis = f"**{black} vann** (0-1)"
        winner_side = 'Svart'
    elif result_raw == '1/2-1/2':
        result_vis = "**Remis** (½-½)"
        winner_side = 'Remis'
    else:
        result_vis = result_raw
        winner_side = '?'

    # Tidskontroll i min
    try:
        tc_sek = int(time_ctrl.split('+')[0])
        tc_vis = f"{tc_sek // 60} min" if tc_sek >= 60 else f"{tc_sek}s"
    except Exception:
        tc_vis = time_ctrl

    opening_str = f"{opening} ({eco})" if eco and eco != opening else opening

    # ── Be Claude om analyse per trekk ───────────────────────────────────────
    trekkliste = "\n".join(
        f"{nr}. {'Kvit' if nr % 2 == 1 else 'Svart'}: {san}"
        for nr, san, fan, _, _ in svg_refs
    )
    analyse_prompt = f"""Du er ein sjakklærar for Katchi (sjakkentusiast, {black_elo} rating).

PARTI: {white} ({white_elo}) mot {black} ({black_elo})
RESULTAT: {result_vis}
FYRSTE TREKK: {opening_seq}
ALLE TREKK:
{trekkliste}

Oppgåve 1 — Identifiser åpningen: Skriv éi linje:
OPNING: [fullt åpningsnamn på norsk, t.d. "Engelsk åpning", "Siciliansk forsvar, Najdorf", "Fransk forsvar", "Englund-gambiten avslått"]

Oppgåve 2 — Gi EI kort setning per trekk (max 25 ord). Bruk dette eksakte formatet:
TREKK_1: [setning]
TREKK_2: [setning]
...
TREKK_{len(svg_refs)}: [setning]
OPPSUMMERING: [2-3 setningar om partiet totalt — kva avgjorde utfallet?]

Bruk sjakkterminologi (gaffel, binding, rokade, opent spel osv). På norsk."""

    print(f"  [chess] Ber om analyse ({len(svg_refs)} trekk)...")
    analyse_rå = ""
    with _get_client().messages.stream(
        model=MODEL, max_tokens=2500,
        messages=[{"role": "user", "content": analyse_prompt}]
    ) as stream:
        for chunk in stream.text_stream:
            analyse_rå += chunk

    # Parse OPNING: frå Claude (bruk berre viss PGN-headers mangla det)
    opning_m = re.search(r'OPNING:\s*(.+)', analyse_rå)
    if opning_m:
        detected_opening = opning_m.group(1).strip()
    else:
        detected_opening = ''

    # Bestem endeleg opningsstreng: PGN-header > Claude > ECO-kode > ukjend
    if opening:
        opening_str = f"{opening} ({eco})" if eco else opening
    elif detected_opening:
        opening_str = f"{detected_opening} ({eco})" if eco else detected_opening
    elif eco:
        opening_str = eco
    else:
        opening_str = "—"

    # Parse TREKK_N: → dict
    analyse_per_trekk: dict[int, str] = {}
    oppsummering = ""
    for m in re.finditer(r'TREKK_(\d+):\s*(.+?)(?=\nTREKK_\d+:|\nOPPSUMMERING:|$)',
                         analyse_rå, re.DOTALL):
        analyse_per_trekk[int(m.group(1))] = m.group(2).strip()
    opp_m = re.search(r'OPPSUMMERING:\s*(.+)', analyse_rå, re.DOTALL)
    if opp_m:
        oppsummering = opp_m.group(1).strip()

    # ── Materialbalanse-graf (Mermaid xychart-beta) ───────────────────────────
    n_moves    = len(svg_refs)
    mat_str    = ", ".join(str(v) for v in mat_vals)
    y_max      = max(15, max(mat_vals) + 2)
    y_min      = min(-15, min(mat_vals) - 2)

    mermaid_graf = f"""```mermaid
xychart-beta
    title "Materialbalanse — {white} vs {black}"
    x-axis "Trekk" 0 --> {n_moves}
    y-axis "Fordel (brikkepoeng)" {y_min} --> {y_max}
    line [{mat_str}]
```"""

    # ── Bygg partikort ────────────────────────────────────────────────────────
    linjer = [
        header,
        "",
        "## 📋 Partikort",
        "",
        f"| | Kvit | Svart |",
        f"|---|---|---|",
        f"| **Spelar** | {white} | {black} |",
        f"| **Rating** | {white_elo} | {black_elo} |",
        f"| **Resultat** | {result_vis} | |",
        "",
        f"**Opning:** {opening_str}  ·  **Trekk:** {n_moves}  ·  **Dato:** {game_date}  ·  **Tid:** {tc_vis}",
        "",
        "---",
        "",
        "## 📈 Materialutvikling",
        "",
        mermaid_graf,
        "",
        "> Positiv verdi = kvit fordel · Negativ = svart fordel · Kvar punkt = etter eit trekk",
        "",
        "---",
        "",
        "## ♟️ Trekkvis analyse",
        "",
    ]

    # ── Trekk for trekk: figurnotasjon + brett + analyse ─────────────────────
    for nr, san, fan, fname, mat_etter in svg_refs:
        side    = "Kvit" if nr % 2 == 1 else "Svart"
        komment = analyse_per_trekk.get(nr, "")
        mat_tag = f"+{mat_etter}" if mat_etter > 0 else str(mat_etter)

        linjer.append(f"**{nr}. {fan}** · *{side}* · material: `{mat_tag}`")
        linjer.append(f"![[{fname}|360]]")
        if komment:
            linjer.append(f"> {komment}")
        linjer.append("")

    # ── Oppsummering ──────────────────────────────────────────────────────────
    if oppsummering:
        linjer += [
            "---",
            "",
            "## 📝 Oppsummering",
            "",
            oppsummering,
            "",
        ]

    filepath.write_text("\n".join(pre + linjer + post), encoding="utf-8")
    print(f"  [chess] OK — partikort + graf + {n_moves} analyserte trekk → {filepath.name}")


# ── Auto-linking (køyrer automatisk på kvar endra fil) ───────────────────────
_note_names_cache   = []
_names_cache_time   = 0

def _oppdater_notatnamn():
    global _note_names_cache, _names_cache_time
    if time.time() - _names_cache_time < 60:
        return
    _note_names_cache = [
        p.stem for p in VAULT.rglob("*.md")
        if not any(d in p.parts for d in IGNORE) and not p.name.startswith("_")
    ]
    _names_cache_time = time.time()

def autolink_fil(filepath):
    """Legg [[wikilenker]] inn i éi fil automatisk. Ingen API-kall."""
    if filepath in _writing_files:
        return
    _oppdater_notatnamn()
    try:
        txt = filepath.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return

    eksisterande = {m.lower() for m in re.findall(r"\[\[([^\]|]+?)(?:\|[^\]]+?)?\]\]", txt)}
    ny_txt    = txt
    endringar = []

    for namn in sorted(_note_names_cache, key=len, reverse=True):
        if namn.lower() == filepath.stem.lower(): continue
        if namn.lower() in eksisterande: continue
        pattern = r'(?<!\[\[)(?<!\[)(?<!`)\b(' + re.escape(namn) + r')\b(?!\]\])(?!`)'
        matches = list(re.finditer(pattern, ny_txt, flags=re.IGNORECASE))
        if matches:
            m       = matches[0]
            ny_txt  = ny_txt[:m.start()] + f"[[{m.group(1)}]]" + ny_txt[m.end():]
            endringar.append(namn)
            eksisterande.add(namn.lower())

    if endringar:
        _writing_files.add(filepath)
        try:
            filepath.write_text(ny_txt, encoding="utf-8")
            print(f"  [auto-link] {filepath.stem}: +{len(endringar)} → {', '.join(endringar)}")
        finally:
            time.sleep(0.5)
            _writing_files.discard(filepath)


# ── Dispatch-tabell ───────────────────────────────────────────────────────────
HANDLERS = {
    "Ciel-sjekk:":    ("Ciel-sjekk",    handle_sjekk),
    "Ciel-diagram:":  ("Ciel-diagram",  handle_diagram),
    "Ciel-skriv:":    ("Ciel-skriv",    handle_skriv),
    "Ciel-kryssref:": ("Ciel-kryssref", handle_kryssref),
    "Ciel-latex:":    ("Ciel-latex",    handle_latex),
    "Ciel-eksamen:":  ("Ciel-eksamen",  handle_eksamen),
    "Ciel-forslag:":  ("Ciel-forslag",  handle_forslag),
    "Ciel-A:":        ("Ciel-A",        handle_A),
    "Ciel-chess:":   ("Ciel-chess",   lambda q,f,p,po,h: handle_chess(q,f,p,po,h, chess.WHITE)),
    "Ciel-chess-W:": ("Ciel-chess-W", lambda q,f,p,po,h: handle_chess(q,f,p,po,h, chess.WHITE)),
    "Ciel-chess-B:": ("Ciel-chess-B", lambda q,f,p,po,h: handle_chess(q,f,p,po,h, chess.BLACK)),
    "Ciel:":         ("Ciel",          handle_stc),
}


# ── Prosesser éi fil ──────────────────────────────────────────────────────────
_writing_files = set()

def process_file(filepath):
    if filepath in _writing_files:
        return
    try:
        content = filepath.read_text(encoding="utf-8")
    except Exception as e:
        print(f"  Lesefeill {filepath.name}: {e}"); return

    lines = content.splitlines()

    for i, line in enumerate(lines):
        stripped = line.strip()

        # Finn kva prefiks som er brukt (lengre prefiks sjekka fyrst)
        prefix_key = None
        for p in PREFIXES:
            if stripped.startswith(p):
                prefix_key = p
                break
        if not prefix_key:
            continue

        q = stripped[len(prefix_key):].strip()

        # Sjakk-prefiks: samle PGN frå etterfølgjande linjer (PGN er alltid flerlinjer)
        if prefix_key in CHESS_PREFIXES:
            pgn_lines = [q] if q else []
            extra     = 0
            for fl in lines[i + 1:]:
                fs = fl.strip()
                if fs.startswith("**Svar ("):   break
                if any(fs.startswith(p) for p in PREFIXES): break
                pgn_lines.append(fl)
                extra += 1
                # Stopp etter resultat-linje (1-0, 0-1, 1/2-1/2)
                if fs in ("1-0", "0-1", "1/2-1/2", "*") or \
                   any(fs.endswith(r) for r in ("1-0", "0-1", "1/2-1/2")):
                    break
            q    = "\n".join(pgn_lines).strip()
            pre  = lines[:i + 1]
            post = lines[i + 1 + extra:]
        elif not q:
            continue
        else:
            # Krev doble hermeteikn: Ciel: ""spørsmål""
            # Obsidian auto-parar " → "" so brukaren treng berre trykke " éin gong i kvar ende
            # Ventar på avsluttande "" før agenten startar å generere
            if not (q.startswith('""') and q.endswith('""') and len(q) > 4):
                continue  # Ikkje ferdig skrive enno
            q    = q[2:-2].strip()   # Fjern "" frå begge endar
            if not q:
                continue
            pre  = lines[:i + 1]
            post = lines[i + 1:]

        # Sjekk om allereie besvart
        tag, handler_fn = HANDLERS[prefix_key]
        nxt = post[0].strip() if post else ""
        if nxt.startswith(f"**Svar ({tag})"):
            continue

        today  = date.today().strftime("%Y-%m-%d")
        header = f"**Svar ({tag}) — {today}:**"

        print(f"  [{tag}] {filepath.name}: {q[:50].replace(chr(10),' ')}")
        _writing_files.add(filepath)
        try:
            handler_fn(q, filepath, pre, post, header)
            print(f"  OK\n")
        except Exception as e:
            print(f"  Feil: {e}\n")
        finally:
            time.sleep(1)
            _writing_files.discard(filepath)

        break  # Éin spørsmål om gongen per fil; neste spørsmål kjem i neste poll-runde


# ── Hovudløkke ────────────────────────────────────────────────────────────────
def main():
    print("Ciel-agent v3 startar")
    print(f"Vault : {VAULT.name}")
    print(f"Modell: {MODEL}")
    print("Prefiks: Ciel: | Ciel-sjekk: | Ciel-A: | Ciel-diagram: | Ciel-skriv: | "
          "Ciel-kryssref: | Ciel-latex: | Ciel-eksamen: | Ciel-forslag: | Ciel-chess:")
    print("Overvaker alle .md-filer — Ctrl+C for aa stoppe\n")
    _get_client()  # valider at API-nøkkelen finst før vi startar løkka

    file_mtimes: dict = {}
    print("Aktiv. Ventar på StC:-spørsmål i alle .md-filer...\n")

    try:
        while True:
            time.sleep(POLL_SECS)

            for filepath in VAULT.rglob("*.md"):
                if any(d in filepath.parts for d in IGNORE): continue
                if filepath in _writing_files: continue

                try:
                    mtime = filepath.stat().st_mtime
                except Exception:
                    continue

                if file_mtimes.get(filepath) == mtime:
                    continue

                file_mtimes[filepath] = mtime

                # Les berre filer som faktisk inneheld eit StC-prefiks
                try:
                    txt = filepath.read_text(encoding="utf-8", errors="ignore")
                except Exception:
                    continue

                if any(p in txt for p in PREFIXES):
                    process_file(filepath)
                else:
                    autolink_fil(filepath)  # Auto-link vanlege notat utan Ciel:-prefiks

    except KeyboardInterrupt:
        print("\nStoppa.")


if __name__ == "__main__":
    main()
