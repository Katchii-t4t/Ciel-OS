# Project Ciel 🌙

Personleg AI-assistent bygd inn i Obsidian. Køyrer lokalt på PC-en, brukar Anthropic Claude API.

## Kva er Ciel?

Ciel er eit sett Python-agentar som overvaker Obsidian-vaulten og svarar automatisk på spørsmål skrivne direkte i notat. Skriv `Ciel: kva er mitokondrier?` i eit notat og Ciel svarar med typewriter-effekt medan du ser på.

## Kommandoar

| Kommando | Beskriving |
|----------|------------|
| `Ciel: spørsmål` | Generelt svar frå vault + Claude |
| `Ciel-A: spørsmål` | Djuptgåande svar med SNL + Wikipedia + PubMed |
| `Ciel-sjekk: tekst` | Faktasjekk tekst mot vault og kjelder |
| `Ciel-diagram: tema` | Lag Mermaid-diagram |
| `Ciel-skriv: instruksjon` | Skriv/omarbeid tekst |
| `Ciel-latex: formel` | Konverter til LaTeX |
| `Ciel-eksamen: tema` | Generer eksamensøving |
| `Ciel-forslag: spørsmål` | Metodologiske forslag |
| `Ciel-kryssref: tema` | Krysskoblingar i vault |

## Agentar

| Fil | Funksjon |
|-----|----------|
| `stc_agent.py` | Hovudagent — svarar på Ciel-kommandoar i Obsidian |
| `stc_lyd.py` | Lydagent — transkriberer med NB-Whisper → Obsidian-notat |
| `stc_pdf.py` | PDF-agent — les og svarar på spørsmål om PDF-embeddar |
| `stc_autolink.py` | Autolenkjar — lagar wikilenker mellom notat |
| `stc_morning.py` | Morgenoversikt — dagleg samandrag |
| `stc_goodnotes.py` | GoodNotes (handskrift) → Obsidian-notat via Claude Vision |
| `ciel_server.py` | **Backend-server (Fase 1)** — FastAPI som eksponerer Ciel for nettbrett/telefon |

## GoodNotes → Obsidian (handskrift via Claude Vision)

GoodNotes har ingen open API, og notata er handskrift (blekk). Broa: eksporter
GoodNotes-sider som **PDF eller bilete** inn i `AI/GoodNotes/inn/` (synka via
vaulten). `stc_goodnotes.py` renderar sidene, les handskrifta med **Claude Vision**,
lagar eit strukturert nynorsk-notat, rutar det til rett fagmappe og arkiverer
originalen til `AI/GoodNotes/arkiv/`.

```powershell
python stc_goodnotes.py            # vakt-modus (overvaker inn/)
python stc_goodnotes.py <fil>      # prosesser éi fil med ein gong
```

Krev `pymupdf` + `pillow`. Vision-modell overstyrbar med `CIEL_VISION_MODEL`
(standard `claude-sonnet-4-6` — sterk på handskrift). Uleselege parti vert markerte,
ikkje gjetta. Bileta blir sende til Anthropic (Claude Vision), som PDF/lyd-agentane.

**Ruting:** `vel_mappe()` les dei EKTE mappene i vaulten og lar Ciel velje den
best passande basert på innhaldet (med nøkkelord-heuristikk som fallback).

**Del → Ciel (tablet):** GoodNotes → del PDF/bilete → vel **Ciel**. Appen tek imot
fila (nativ `ACTION_SEND` i `MainActivity`), sender den til `POST /api/goodnotes`
på hjernen, som legg den i `inn/` → notat. Ingen manuell lagring. Server-endepunktet
og ruting er verifiserte ende-til-ende; sjølve share-handoffen testar du frå GoodNotes.

## PDF i notatet (dra inn → samandrag med ein gong)

`stc_pdf_embed.py` — dra ein PDF inn i eit forelesnings-notat (Obsidian lagar
`![[fila.pdf]]`). Ciel oppdagar embed-en innan nokre sekund og skriv eit strukturert
nynorsk-samandrag rett inn i SAME notat, i eit `[!abstract]`-callout under klamma.
Ingen kommando, ingen `PDF_inn`-kanal.

- Idempotent: kvar embed prosesserast berre éin gong (usynleg `<!-- ciel-pdf:… -->`-markør).
- Vision-fallback (`claude-sonnet-4-6`) for skanna PDF-ar utan tekst-lag.
- Vakta reagerer når du ENDRAR eit notat (dreg PDF inn) — masse-prosesserer ikkje
  heile vaulten ved oppstart. `--once` prosesserer heile backlog-en.

```powershell
python stc_pdf_embed.py          # vakt
python stc_pdf_embed.py --once   # heile backlog éin gong
```

## Oppsett

### Krav
Backend (Fase 1) — lett sett, ingen torch:
```
pip install -r requirements.txt
```
Lyd-transkribering (Fase 3) i tillegg:
```
pip install transformers accelerate torch
```

### API-nøkkel
Lagra `ANTHROPIC_API_KEY` som Windows User-miljøvariabel (aldri hardkoda i kode).

```powershell
[System.Environment]::SetEnvironmentVariable("ANTHROPIC_API_KEY", "sk-ant-...", "User")
```

### Start
Legg `start_ciel.vbs` i `shell:startup` for autostart ved innlogging.
Eller køyr manuelt:
```
start_stc_agent.bat
start_stc_lyd.bat
```

## Backend-server (Fase 1)

`ciel_server.py` pakkar inn agent-logikken og gjer Ciel tilgjengeleg for tynne
klientar (nettbrett/telefon) over HTTP + WebSocket. PC-en er hjernen; klientane
renderer berre. Berre serveren snakkar med Anthropic — klientane gjer det aldri.

Start:
```powershell
$env:ANTHROPIC_API_KEY = [System.Environment]::GetEnvironmentVariable("ANTHROPIC_API_KEY","User")
python ciel_server.py            # http://0.0.0.0:8765
```
Interaktive API-dokument: `http://localhost:8765/docs`

| Endepunkt | Funksjon |
|-----------|----------|
| `POST /api/ask` | Spør Ciel (`{question, deep, context}`) → heile svaret |
| `WS /ws/stream` | Token-for-token typewriter (`{token}` per bit) |
| `WS /ws/events` | Push: modusbyte, girl-mode, status |
| `GET /api/vault/notes` | Siste notat i vaulten |
| `GET /api/vault/note?path=` | Eitt notat sitt innhald |
| `POST /api/command` | Fast allow-liste: `set_mode`, `set_girl_mode`, `open_note`, `search_vault` |
| `GET /api/state` | Gjeldande modus + farge |
| `GET /api/tracker/today` | Gjennomsiktig dagsscore + mild prioritet (Fase 5, Module J) |
| `GET /api/briefing?kind=morning\|evening` | Proaktiv briefing, klar til å lesast høgt (Fase 5, Module F) |
| `GET /api/proactive/due` | Kva proaktive hendingar er due no (planleggjar) |
| `POST /api/transcribe` | Lyd → tekst (Fase 3) |

**Proaktiv planleggjar (Module F):** ein bakgrunnsløkke sender morgon- (kl. 07) og
kveldsbriefing (kl. 21) over `/ws/events` éin gong per dag — Ciel snakkar opp av seg
sjølv, ikkje berre når du spør. Tidene er overstyrbare med `CIEL_MORNING_HOUR` /
`CIEL_EVENING_HOUR`.

**Smart LLM-routing:** billegaste modell som klarar jobben — Haiku for vanlege
spørsmål, Sonnet for djupe (`deep: true`). Overstyrbart med `CIEL_MODEL_*`.

**Tryggleik:** API-nøkkel berre frå miljøvariabel. `/api/command` køyrer berre
handlingar frå ei fast allow-liste (ingen vilkårleg eksekvering), path-traversal
er blokkert, og kvar kommando vert logga til `logs/action_log.jsonl`.

### Autostart av hjernen
`start_ciel_server.vbs` startar serveren heilt usynleg ved innlogging. Legg han i
`shell:startup`. Han les `ANTHROPIC_API_KEY` direkte frå den lagra User-variabelen
og brukar `python.exe` med skjult vindauge (ikkje `pythonw.exe` — det gjev
`sys.stdout = None` og krasjar agent-koden lydlaust).

### Helsesjekk
`ciel_doctor.py` testar heile hjernen ende-til-ende (server, vault, API-nøkkel, eit
ekte Claude-svar gjennom pipelinen, modus-state) og gir ein ✅/❌-rapport:
```powershell
python ciel_doctor.py     # serveren må køyre
```

## Modell
- **Claude (vanleg):** `claude-haiku-4-5` (rask, billeg, god nok for notat)
- **Claude (djup):** `claude-sonnet-4-6` (Ciel-A / `deep: true`)
- **Whisper:** `NbAiLab/nb-whisper-medium` (norsk-optimalisert, ~1.5 GB)

## Nettbrett-klient (Fase 2)

`ciel_app/` — Flutter-app (tynn klient) som koplar seg til PC-hjernen over
WiFi/Tailscale. Viser Ciel-orben (port av orb-prototypen til CustomPainter),
har eit spør-felt med token-for-token typewriter, og speglar modus-fargen.

```powershell
cd ciel_app
flutter pub get
flutter run -d chrome          # førehandsvis i nettlesar
# flutter run -d <tablet-id>   # på Tab S10+ (krev Android SDK)
flutter build web              # → build/web
```

Server-URL vert lagra på eininga (standard `http://192.168.10.194:8765`).
Lang-trykk på orben → innstillingar (server-URL, modus, girl mode).

| Fil | Innhald |
|-----|---------|
| `lib/main.dart` | App-rot, mørkt tema |
| `lib/screens/home.dart` | Heimskjerm: orb, spør-felt, svar, innstillingar |
| `lib/services/ciel_api.dart` | REST + WebSocket-klient mot ciel_server.py |
| `lib/widgets/orb.dart` | Ciel-orben (CustomPainter) — gull + girl mode |

## Nettbrett — Fase 4 (Ciel OS-kjensla)
`ciel_app` er no ei full launcher-oppleving på Tab S10+:
- **Heimskjerm-launcher** (HOME-intent): orben *er* heimskjermen, kant-til-kant svart.
- **S Pen → handling:** skriv eit ord på orben → ML Kit (lokalt) → opnar app /
  startar scene / spør Ciel. Normalisert matching + fleire tolkingar (toler "good notes").
- **Orb-til-hjørne:** flutter_overlay_window — orben svever over andre appar (matchar
  modus-farge), trykk → tilbake til Ciel. (Krev batteri "Ubegrensa" på Samsung.)
- **Auto-farge:** girl mode (trans-flagg) som standard; server klassifiserer tema →
  modus/girl-mode over /ws/events.
- **Velkomstport (SPEC §5):** pennord (sha256) + fingeravtrykk + fjes (BiometricPrompt).
  Opplevingslag — ikkje einings-tryggleik (One UI-låsen er framleis lag 1).
- **Levande wallpaper:** WallpaperService teiknar orben (partiklar orbiterer kjernen
  som eit solsystem) som låsskjerm/heim-bakgrunn. Statisk PNG-variant òg.
- **Velkomst-helsing:** tidsstyrt "God morgon/ettermiddag/kveld, Dr. Katchi".
- Eige Ciel-ikon. Bygg: `flutter build apk --release`.

## Portabilitet
Vault-stien vert no funnen automatisk under `%USERPROFILE%\OneDrive\Obidian stasj`
(overstyr med miljøvariabelen `CIEL_VAULT`). Ingen hardkoda brukarnamn.

## Vault-struktur
```
Obsidian-vault/
├── AI/Lyd/Lyd_inn/     ← dropp lydfiler her
├── AI/Lyd/Lyd_arkiv/   ← arkiverte lydfiler
└── Studie/Medisin/...  ← notat havnar her
```

---
*Del av Project Ciel — personleg Obsidian-assistent for Katchi*
