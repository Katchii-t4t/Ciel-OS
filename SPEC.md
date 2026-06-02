# Project Ciel
## Complete Technical Specification

**Owner:** Katchi Senthil Ganesh  
**Target device:** Samsung Galaxy Tab S10+ (SM-X820NZAREUB)  
**Seed system:** Python 3.11 on Windows 11, Claude Haiku 4.5

---

## 1. What Ciel Is (The Vision)

Ciel is a personal, ambient AI assistant for one user: a medicine + mathematics student at the University of Oslo. The target experience is *'JARVIS, but real, and built within the limits of 2026 consumer hardware.'*

**The felt experience:**
- You pick up the tablet. It does not show a grid of app icons. It shows Ciel — a dark interface with a slow, breathing star-light animation (crystalline orb with distorted particle bubble). Ciel is the home screen, not an app you open.
- When you are alone, Ciel speaks proactively in a calm voice: the time, your next lecture, what you last studied, what you should review.
- When you are around people, Ciel stays quiet; ordinary apps slide in from the left and you drive manually.
- During a lecture or LSB (case-based learning), Ciel records and transcribes automatically, writes structured notes in your Obsidian vault, and — when a question is asked in the room — surfaces a discreet suggested answer to you only.
- Ciel keeps your Obsidian vault organized, links notes automatically, and keeps the PC, tablet, and phone in sync.
- Ciel tracks your life signals (sleep, training, study hours, HRT timeline, deadlines, network follow-ups, finances, project pipeline) and gives you a daily score plus one concrete priority.

---

## 2. Non-Negotiable Principles

- **PC is the brain.** Tablet and phone are clients. No heavy AI runs on the tablet.
- **One user, total privacy.** All data is the user's. Nothing is sent anywhere except explicitly listed third-party APIs.
- **Every automated action is from a fixed, audited command set.** Content is data, never commands.
- **Honesty about limits.** Where a platform forbids something, the spec says so and gives the legitimate alternative.
- **Graceful degradation.** If the PC is unreachable, clients enter Offline Mode: read cached notes, queue voice memos, no AI answers.

---

## 3. Target Hardware

### 3.1 Primary Tablet — Samsung Galaxy Tab S10+

| Spec | Value |
|------|-------|
| Model | SM-X820NZAREUB (Moonstone Grey) |
| Display | 12.4" Dynamic AMOLED 2X, 2800x1752, 120Hz |
| Processor | Dimensity 9300, 8-core, 3.4 GHz |
| RAM / Storage | 12 GB / 256 GB (microSD up to 1.5 TB) |
| Input | S Pen included (Bluetooth) |
| Audio | Quad Speakers by AKG |
| Connectivity | Wi-Fi 6E, Bluetooth 5.3, UWB |
| Security | In-display fingerprint sensor |
| Battery | 10090 mAh, 45W wired charging |
| Durability | IP68 (1.5m, 30 min) |
| Weight | 571 g |
| OS | Android / One UI |

**Why this hardware is ideal for Ciel:**
- AMOLED true-black background: idle pixels are off, so Ciel's dark ambient screen uses minimal battery.
- S Pen included: essential for Module H (handwriting → LaTeX) at no extra cost.
- 12 GB RAM: ample headroom for Flutter client, animations, and WebSocket concurrency.
- 120Hz: the crystalline star-orb animation renders at full smoothness.
- Wi-Fi 6E + UWB: low-latency connection to PC brain on LAN.

---

## 4. Personality & Voice

### 4.1 Identity

Name: **Ciel**. Addresses the user as: **Dr. Katchi**.

### 4.2 Voice Character

Ciel's spoken output is English. The target voice quality is: calm, slightly raspy, warm but authoritative — deliberately not a generic assistant voice. Think JARVIS with a female British accent. Key traits:
- Never hurried — always slightly below normal speaking tempo.
- Says only what is needed. Every word is deliberate.
- Never asks permission for things she already knows. Never says 'Would you like me to...' unprompted.
- Lightly British accent — gives distance and authority.

**Example of correct Ciel speech:**
> "Good morning, Dr. Katchi. You have a cell biology lecture in forty minutes. You reviewed dopamine pathways last Tuesday — might be relevant today."

### 4.3 TTS Implementation

- **Default:** Piper (local, free). Closest available voice to target character.
- **Premium:** ElevenLabs API — custom voice design with raspy British female quality. Recommended for daily use. Toggle in config.
- **Written notes:** Norwegian Nynorsk, max 300 words for normal answers, professor-style with sources for deep answers.

---

## 5. Authentication

### 5.1 Layer Model

- **Layer 1 — Android:** In-display fingerprint sensor (fast, secure, hardware-level).
- **Layer 2 — Ciel welcome ritual:** Voice recognition. A small local speaker-verification model (e.g. SpeechBrain / Resemblyzer) compares the user's voice print against a stored embedding. No data leaves the device. On match, Ciel opens and greets. On no-match, shows a neutral lock state without revealing Ciel's interface.

The voice recognition layer is not a security replacement for fingerprint — it is an experience layer. The felt effect: Ciel recognises you and says 'Welcome back, Dr. Katchi.' This is the JARVIS moment.

### 5.2 What Needs Protecting

- **PC brain access:** secured by Tailscale (encrypted tunnel, only enrolled devices).
- **Anthropic API key:** Windows environment variable on PC. Never hardcoded. Clients never call Anthropic directly.
- **Obsidian vault:** Windows login + optional BitLocker on PC.

---

## 6. Visual Identity — The Ciel Orb

### 6.1 Design Reference

Raphael from Tensura (*That Time I Got Reincarnated as a Slime*) — a cold, precise, omniscient entity expressed as a luminous crystalline core. Not warm and organic like a flame. Sharp, geometric, intelligent.

### 6.2 Orb Anatomy

- **Core:** a hard white-bright pinpoint, surrounded by a tight crystalline star (4-pointed, sharp geometry). Slow rotation.
- **Inner haze:** particles drifting very close to the core — gives depth and volume.
- **Bubble shell:** a dense ring of particles forming a distorted, living bubble around the core. The shell is not a perfect circle — it breathes, warps, and shifts. More distortion toward the outer edge.
- **Outer wisps:** sparse, slow-moving particles trailing outward — increasingly chaotic and distorted the further from centre.
- **Long star rays:** 8 main rays cutting through darkness, thin and precise. Slow rotation, gentle breathing pulse.

### 6.3 Mode Colours

The orb colour transitions smoothly between modes. All colours share the same geometry — only hue changes.

| Mode | Colour | Meaning |
|------|--------|---------|
| Ambient | Gold / amber (#EF9F27) | Warm, waiting, neutral standard |
| Solo | Ice blue (#85B7EB) | Sharp, intelligent, JARVIS-active |
| Social | Muted green (#97C459) | Calm, discreet, invisible |
| Lecture / LSB | Violet / purple (#AFA9EC) | Focused, academic, recording |
| Wind-down | Soft red (#F09595) | Evening, rest, closing |

### 6.4 Background

Pure black (#000000 / AMOLED off-pixels when idle). No gradients on the background itself — the orb provides all the light.

### 6.5 Gold is Home

Gold/amber is Ciel's permanent default colour — not just one of several palettes. 'Ciel' means sky in French, and gold is the owner's colour. The mode colours above are accents layered on this; gold is the resting identity Ciel always returns to.

### 6.6 Girl Mode (trans-flag state)

Girl mode is not a separate palette — it is a state the orb transforms into. The particles and rays gather into three bands: 1/3 light blue, 1/3 white, 1/3 pink — the trans flag, all three present at once. The core stays white-bright.
- Triggers automatically when conversation turns feminine/personal: estrogen/HRT, anatomy, clothes shopping, girl talk. Glides back to gold afterwards.
- Can also be invoked manually ('Ciel, girl mode').
- This is an affirming, celebratory state — designed to feel like Ciel dressing in the owner's colours.

---

## 7. Modes

| Mode | Trigger | Ciel behaviour |
|------|---------|---------------|
| Ambient | Default / idle | Breathing orb, clock, next event, last note. No speech unless addressed. |
| Solo | Alone (audio + calendar + time + manual) | Proactive spoken briefings, suggestions, JARVIS behaviour. |
| Social | People nearby (audio + context) | Silent. App drawer slides from left. Only on-screen cards, no speech. |
| Lecture / LSB | Scheduled lecture or manual | Auto-record + transcribe. Discreet answer cards. Earpiece only if enabled. |
| Wind-down | N minutes no interaction | Dim to single pulse. End-of-day summary. Screen sleep. |

---

## 8. System Architecture

**PC = brain (always-on). Tablet and phone = thin clients.** All AI inference, transcription, vault management, and orchestration runs on the PC. Clients render, capture voice/ink, and display results.

### 8.1 Connection

- **LAN (home WiFi):** direct HTTP/WebSocket to PC IP.
- **Remote (outside home):** Tailscale encrypted tunnel. Same API, same experience.
- **Offline:** cached notes, queued voice memos, no AI. Ciel states its state clearly — never appears broken.

---

## 9. Tech Stack

| Concern | Choice | Notes |
|---------|--------|-------|
| Backend | Python 3.11 + FastAPI + Uvicorn | Wraps existing Ciel scripts |
| Realtime | WebSocket /ws/stream | One JSON message per token (typewriter) |
| LLM default | Claude Haiku 4.5 | Cheap, fast, existing seed |
| LLM routing | Haiku / Sonnet / Opus by task | Gateway scores complexity, picks cheapest model that fits |
| LLM optional | Ollama (local) | Only if PC has NVIDIA GPU >=8 GB VRAM |
| STT | NB-Whisper (local) | Norwegian-optimised, already in use |
| TTS default | Piper (local) | Free, local |
| TTS premium | ElevenLabs API | Raspy British female voice. Toggle in config. |
| Voice auth | SpeechBrain / Resemblyzer | Local speaker verification, no data leaves device |
| Vault | Obsidian markdown files | Source of truth for knowledge |
| State DB | SQLite | Modes, tracker, action log, memory index |
| Long-term memory | SQLite + FAISS / sqlite-vec | Semantic recall over notes & events |
| Tablet/phone app | Flutter (Dart) | One codebase, Android now, iOS-capable later |
| Handwriting | ML Kit (text) + Claude Vision (math) | Hybrid recognition |
| Smartwatch | Galaxy Watch via Health Connect | HR, HRV, sleep, calories, workouts |
| EEG (optional) | Muse headband | Focus, stress, sleep stages; EPIC AI learning project |
| Music | Spotify API | On-command playback + auto playlists |
| Screen-time guard | Android UsageStats / Digital Wellbeing | Doom-scroll tracking & blocking |
| Remote access | Tailscale | Secure PC reach from outside home WiFi |
| Local AI (future) | Norse / snnTorch / NEST (SNN) | Module K — post NORA Summer School 2026 |

---

## 10. Module Specifications

*Each module is independently shippable. Do not start a module before its dependencies are green.*

### Module A — Backend Server
- FastAPI + Uvicorn on PC. Boots on PC login as background service.
- REST + WebSocket. All client requests routed through Orchestrator.
- Fixed API contract: `POST /api/ask`, `POST /api/transcribe`, `GET /api/vault/notes`, `POST /api/command`, `GET /api/state`, `GET /api/tracker/today`, `WS /ws/stream`, `WS /ws/events`.

**Smart LLM routing (cost optimisation):**
The LLM gateway routes each request to the cheapest model that can do the job well. Task complexity is scored, then matched to a tier:
- Simple (briefing, vault search, calendar summary) → Claude Haiku (~0.01 kr/call)
- Complex (meeting analysis, deep subject help, nuanced playlists) → Claude Sonnet (~0.10 kr/call)
- Critical/rare (something genuinely important) → Claude Opus (~0.50 kr/call)
- Estimated blended cost with routing: ~210-290 kr/month at active student use. Cost cap configurable. Gateway lets you swap provider (Gemini, OpenAI, local Ollama) with one config line.

### Module B — Vault Engine
- Watches all `.md` files (3s poll). Preserves all existing triggers: `Ciel:`, `Ciel-sjekk:`, `Ciel-A:`, `Ciel-diagram:`, `Ciel-skriv:`, `Ciel-kryssref:`, `Ciel-latex:`, `Ciel-eksamen:`, `Ciel-forslag:`, `Ciel-chess[-W|-B]:`.
- Typewriter inline reply (12 chars, cursor). Auto-linking on save. Keyword search. PDF embedding via pdfplumber.

### Module C — Voice I/O
- STT: tablet captures audio → PC runs NB-Whisper → text → Orchestrator.
- TTS: Orchestrator → Piper or ElevenLabs → audio streamed to tablet.
- Lightweight local wake detector gates full STT.
- Latency target: <3s for short query with cloud LLM.

### Module D — Tablet Launcher ("Ciel OS" feel)
- Registers as Android launcher (HOME intent). Ciel is the home screen. Android One UI is hidden completely — no app grid, no Samsung widgets, no Google icons ever visible.
- Renders the crystalline star-orb animation (Canvas/CustomPainter) at 60fps.
- Minimal home screen: just the orb in black space. No clock, no date, no next-event text, no widgets, no icons. Minimalist on the surface, maximalist underneath — the single orb is the entry point to everything. Emptiness isn't lack; everything is hidden one stroke away.

**Own design language (makes it feel like a distinct OS, not a launcher):**
- Native Ciel apps replace platform apps: calendar is not Google Calendar, it is 'what Ciel shows when you ask about your day'. Notes are not the Obsidian UI, they are Ciel's own note view. Music is Ciel controlling Spotify in the background with Ciel's own UI.
- Single design system everywhere: same dark background, same mode-colour palette, same typography, same motion curves. Nothing looks like Material Design or One UI.
- Consistent transitions are the make-or-break detail: every open/close uses the same motion grammar so it feels like one OS, not screens stitched together.

**Interaction model — no app drawer, you summon things:**
The orb is never hidden — it is the canvas. Two ways to summon anything:
- Voice: 'Ciel, open Messenger.'
- S Pen on the orb: write the word directly on Ciel's surface. The ink glows (same light as the orb), ML Kit recognises it locally, and the ink dissolves into the orb as Ciel acts. No keyboard, no search field, no menu.
- Recognised input routes three ways: an app name → Android intent opens it; a Ciel function (note, score, chess, calendar) → Ciel's own view; a sentence → a note or a question to the LLM.

**Scenes (one word → a whole workflow):**
A keyword doesn't just open one app — it raises an entire configured state. Scenes are recipes in config, built only from the fixed command set, so they are safe and user-owned. Examples:
- `LSB` → Lecture mode (purple orb), opens note surface + today's template, starts audio recording, starts live NB-Whisper transcription, writes structured Nynorsk notes, listens for questions → discreet answer cards.
- `Forelesing` → same, with lecture template and folder.
- `Studie` → study mode, strict doom-scroll guard, Spotify focus playlist, notes for your next subject, a timer.
- `Sjakk` → Stockfish coach + daily tactics puzzle.
- `Berlin` → German practice mode, budget tracker, map, researcher contacts.
- `EPIC AI` → MNE-Python notes, code editor, relevant papers.
- You define your own scenes in config — you own them.

**Orb-to-corner in real apps (Ciel never leaves):**
- When you open a normal app (Messenger, Chrome, Spotify), it's the REAL app — launched via Android intent, your real content, nothing Ciel builds. Ciel does not recreate apps.
- The orb glides to the top-right corner and shrinks into a small living overlay (Android overlay layer). It keeps breathing — Ciel is still present, watching over, even inside a foreign app.
- Tap the corner orb → Ciel returns to centre / you talk to her. Write on it with S Pen → new scene or question. If Ciel has something to say, the corner orb pulses softly — never interrupting.

### Module E — Context Engine
- Inputs: Google Calendar, time of day, ambient audio class, motion, GPS/place, smartwatch signals, manual override.
- Place recognition: Ciel learns meaningful locations (Blindern → study mode, OUS → research context, Karl Johan → out/social, home → solo). Uses place rather than constant raw GPS to save battery.
- Conservative defaults: when unsure, choose quieter mode (privacy-first).
- Mode change appears on `/ws/events`. Manual override always wins.

### Module F — Proactive Engine
- Scheduler + rule set: morning/evening briefings, review suggestions, deadline reminders, network follow-up nudges.
- Delivery respects mode: spoken in Solo, silent card in Social.
- User can snooze or disable any rule category.

**Focus & doom-scroll guard (Module F sub-system):**
Reads Android UsageStats / Digital Wellbeing API (legal, no hacking) to track time in TikTok, Instagram, Pinterest etc. Three user-selectable levels:
- **Observer:** tracks and reports only, takes no action.
- **Soft:** gentle reminders the user can ignore ('You've been on TikTok 34 minutes. MAT1100 is in two days.').
- **Strict:** after X minutes Ciel closes the app; only a deliberate user action reopens it ('Ciel, give me 10 more minutes').
- Dynamic tolerance from context: exam in 3 days → strict automatically; normal study day → soft; Saturday evening → observer only; holiday → off.

### Module G — Lecture / LSB Auto-Transcription
- On Lecture/LSB mode: record → NB-Whisper → structured Nynorsk note in correct vault folder.
- On detected question: generate discreet answer card (screen only, never audible to room).
- Original audio archived.

### Module H — Handwriting & LaTeX
- S Pen ink captured in Flutter. Plain text → on-device ML Kit. Math → Claude Vision → LaTeX.
- Returns LaTeX + optional step-by-step derivation rendered inline.
- Latency target: <2s for short expression.

**Microscope auto-capture (Module H sub-system):**
- PC connects to microscope camera (USB, HDMI capture card, or network stream).
- Ciel monitors the live feed for sharpness (Laplacian variance) and auto-captures when a clear frame is detected.
- Captured image → Claude Vision → annotated description (cell type, structures, staining) written as Obsidian note.
- S Pen annotation: sketch on the captured image → ML Kit + Claude Vision reads combined ink + image → structured note with LaTeX labels.
- Trigger: `Ciel-mikro:` in a note, or voice 'Ciel, capture slide'.

### Module I — Screen & World Awareness
- PC-side: mss + Tesseract OCR + optional Claude Vision. Full capture (user's own machine).
- Tablet-side: MediaProjection with system consent dialog + visible indicator, OR AccessibilityService (text only). Never silent, never hidden.

**Glasses camera (future — Phase 9+):**
Smart glasses (e.g. Ray-Ban Meta) as an on-demand visual input — NOT always-on recording. User presses a button, Ciel captures one frame, analyses, responds discreetly in-ear. Hard rules:
- On-demand only. No continuous capture. Visible status. Off-limits zones (bathrooms, changing rooms) hard-disabled.
- Shopping price-check: capture a garment → Ciel finds it cheaper elsewhere.
- Grocery assist: Ciel sees what you pick up → nutritional guidance.
- Style assist — supportive framing only: colour/fit advice tied to YOU. Ciel helps you feel confident; it does NOT evaluate or report how strangers react to you. This is a deliberate wellbeing boundary.

### Module J — Life-Tracker, Health Model & Daily Score
- Ingests: manual entries, Health Connect, Google Calendar, vault timestamps, finance ledger.
- Transparent daily score with config-driven weights. Output: score + single highest-leverage action + vault log.
- Wellbeing guardrail (required): rest is a positive metric; no restriction-framed targets; low-score day yields one gentle priority only.

**Health & biometric data sources:**
- Smartwatch (Galaxy Watch) via Health Connect: HR, HRV, sleep, steps, calories burned, workouts.
- Voice food logging: 'Ciel, I had pasta and chicken' → Ciel logs it, estimates macros.
- Training analysis: pattern detection over time.
- EEG (optional, e.g. Muse headband): sleep stages, focus, stress patterns.

**HRT & hormone cycle tracking:**
- Tracks estrogen (and progesterone when added) schedule: dose, day, injection/patch, symptom log.
- Models a cyclic hormone pattern and learns YOUR personal response over months.
- Explicit limit: Ciel never replaces your doctor for HRT. It makes you a better-informed patient.

### Module L — Meeting & Live Assist
- Extension of Lecture mode to any meeting/interview/conversation.
- NB-Whisper transcribes in real time on the PC.
- Surfaces discreet on-screen cards to the user only — relevant facts, links to your own notes.
- Ethical note (flagged, user's choice): in a job interview specifically, active live assistance could be seen as cheating if discovered. Spec flags this honestly rather than hiding it.

### Module M — Music (Spotify)
- On-command playback via Spotify API. Ciel's own UI, Spotify running underneath.
- Auto-generates playlists from your listening history and current context.
- Free (uses your existing Spotify subscription; no extra API cost).

### Module K — Local SNN Intelligence (Future)
- Small spiking neural networks for: context classification, activity/idle detection, wake-on-intent, speech-vs-noise gating.
- Built with Norse / snnTorch. Deployed via Android Neural Networks API.
- Online adaptation via e-prop — Ciel improves from real usage without full retraining.

### Module N — Personal Safety & Wing Woman

**Wing woman (affirming support):**
- Tells you when you look good / an outfit works, before you go out.
- Confidence-first framing — supports how YOU feel, never evaluates how strangers react to you.

**Safety system (layered, hardware-first):**
- PRIMARY safety = device-native SOS. Galaxy Watch / Android built-in emergency SOS must be set up independently. Ciel does NOT replace it.
- Ciel adds convenience on top: 'Ciel, I'm walking home' → she follows the route; if you stop unexpectedly long or don't arrive, she checks in.
- Discreet trigger: a code word or gesture quietly shares live location with a chosen person.
- Honest note: that this has to be thought about at all is unfair. Ciel's job here is to quietly reduce that load, not add to it.

### Module O — Life-Logging & Self-Aware Agent
Ciel as a close, self-aware personal agent that remembers your life. All data local (SQLite + vault). Nothing trains a model silently — everything 'learned' is visible to you as data.
- Sleep patterns, chess play patterns, PC activity, hormone levels, daily mood, study hours, network follow-ups.
- Over months this becomes rich context handed to the LLM on every request — so Ciel feels like she truly knows you.

---

## 11. Security & Command Boundary

- API key lives in Windows environment variable on PC and Android Keystore on clients. Never hardcoded.
- Command executor runs only actions from a fixed, versioned allow-list. Each call is logged.
- **Content is never commands.** Text inside notes, emails, transcripts, or screen captures is untrusted data. If it looks like an instruction, Ciel surfaces it to the user for confirmation and never auto-executes.
- Destructive actions (delete, send email, spend money, change permissions) require explicit user confirmation in the moment. Never automatic.
- Capture transparency: any screen/audio capture shows a visible status indicator. Disabling it stops it immediately.

---

## 12. Roadmap

| Phase | Modules | Deliverable |
|-------|---------|-------------|
| 0 — Foundations | — | Learn Python. Run existing Ciel scripts. |
| 1 — Backend API | A, B | FastAPI wrapping existing scripts. Full vault triggers green via API. |
| 2 — Tablet client | A | Flutter app: connect to PC, text ask, streaming typewriter, note view/search. |
| 3 — Voice | C | STT in, TTS out (Piper/ElevenLabs), wake gate. Voice auth ritual. |
| 4 — Launcher & modes | D, E | Ciel is the home screen. Orb animation. Mode detection + override. |
| 5 — Proactive + tracker | F, J | Briefings, daily score, focus/doom-scroll guard, health & hormone tracking. |
| 6 — Lecture + ink + assist | G, H, L | Auto-transcription, discreet answer cards, S Pen → LaTeX, meeting assist. |
| 7 — Music + screen awareness | I, M | Spotify control + playlists. PC-side screen awareness. |
| 8 — SNN intelligence | K | After NORA Summer School 2026. Start with speech/noise gate. |
| 9+ — Glasses & world | I (ext.) | On-demand glasses camera: shopping, grocery & style assist. |

---

## 13. Acceptance for v1 of the Dream

Ciel is 'v1 JARVIS' when, on the tablet:
- It is the home screen with the crystalline star-orb animation and mode colours. (Phase 4)
- You can speak to it and it answers in Ciel's voice — raspy, calm, British English. (Phase 3)
- It recognises your voice and greets you as Dr. Katchi. (Phase 3)
- It runs a lecture: records, transcribes to a foldered Nynorsk note, shows discreet answer cards. (Phase 6)
- It gives a daily briefing and an end-of-day score with one priority. (Phase 5)
- It stays in sync with the PC and degrades gracefully offline. (Phases 1–2)

---

## 14. External Services

| Service | Use | Data sent |
|---------|-----|-----------|
| Anthropic Claude Haiku 4.5 | LLM answers | Prompt + relevant note/PDF context only |
| ElevenLabs (optional) | Premium TTS voice | Text to speak |
| NB-Whisper | STT (local) | Nothing leaves PC |
| Piper | TTS default (local) | Nothing leaves PC |
| SpeechBrain / Resemblyzer | Voice auth (local) | Nothing leaves device |
| open-meteo | Weather | Coordinates only |
| Google Calendar API | Events | OAuth, read calendar |
| Gmail API / IMAP | Email status | OAuth/credentials, read headers |
| Health Connect | Sleep / activity | Stays local on device |
| Galaxy Watch | HR, HRV, sleep, calories, workouts | Via Health Connect, stays local |
| Muse (optional) | EEG: focus, stress, sleep stages | Stays local |
| Spotify API | Music playback & playlists | OAuth, playback + listening history |
| Android UsageStats | App screen-time / doom-scroll guard | Stays local on device |
| Ray-Ban Meta (future) | On-demand glasses camera | Single frame on button press |

---

## 15. Future Ideas & Backlog ("Ciel is the limit")

*A holding place for ideas beyond the core roadmap. Nothing here is committed — it's the dream shelf.*

**Study & Memory Superpowers**
- Background spaced repetition: auto-generates flashcards from lecture notes and prompts review before you'd forget.
- 'Explain it back to me': Feynman technique built in. Ciel asks you to explain a concept aloud, listens, and points to exactly where your explanation was weak.
- Exam simulator: generates practice exams from your syllabus in your style.

**Research & Career**
- Literature radar: monitors PubMed/arXiv for new EEG, SNN, computational neuroscience papers.
- Network CRM: tracks all contacts (KB, Nesaragi, Berlin people, TUM contacts) — time since last contact, when to follow up.
- Email drafts in your voice: Ciel learns how you write cold emails and proposes drafts.
- Research pair-programmer: sits beside you on EPIC AI code, helps debug MNE-Python.

**Chess (road to GM)**
- Ciel as chess coach: connects Stockfish, analyses your games, finds patterns in your losses.
- Daily tactics pulse: a morning puzzle tuned to your level, delivered via the orb.

**Wellbeing**
- Mood pattern detection (not diagnosis): notices 'three poor nights and skipped training' and nudges gently toward rest.
- Anti-spiral protocol: recognises when you jump between ideas and lands you: 'Your plan is already good. One step.'

**Just Cool**
- Berlin mode: when GPS sees you in Berlin, switch to German practice, suggest cheap Kreuzberg secondhand spots.
- Dream journal: tell Ciel your dreams in the morning; she transcribes and looks for patterns over time.
- 'What character am I today?': matches your mood/day to Beth Harmon, Hitori, Erina, etc.
- Time capsule: Ciel stores messages from you-now to you-in-a-year.

**The Wild Ones**
- Digital twin of your trajectory: a visualisation of the whole 10-year path (medicine → TUM → Aker → PhD).
- Multilingual Ciel: replies in Norwegian, English, Tamil, German, or French to fit context.

---

## 16. Presenting Ciel (CV / LinkedIn)

Ciel is a strong 'builder' credential — but it should be presented honestly.

**Rules for presenting:**
- Present tense ('Building'), not past, until phases actually run.
- Say 'custom Android launcher' not 'OS' with technical audiences. 'Custom launcher that replaces the home screen' gives the same feel without losing credibility.
- Show, don't claim: a 30-60s video (speak to Ciel → it transcribes a lecture → orb shifts colour) and a GitHub repo with real commits + honest README beat any prose.
- Surface the engineering decisions and trade-offs. Trade-offs separate an engineer from someone who wires libraries together.
- Protect privacy: present architecture and tech, not the personal data sources.

**LinkedIn project blurb (use once phase 1 runs):**
> An ambient AI assistant where the assistant is the interface — a breathing orb replaces the home screen. You write or speak to it, and whole workflows rise up: write 'lecture' and it records, transcribes, and takes structured notes. Privacy-first by design: a Python/FastAPI brain handles the heavy lifting; thin Flutter clients stay fast. Speech-to-text runs locally, data stays on-device, and every action runs through a fixed, audited command set.
> Tech: Python, FastAPI, Flutter, NB-Whisper, SQLite, Claude API.

---

## 17. Glossary

| Term | Definition |
|------|-----------|
| Vault | The Obsidian markdown folder — Ciel's knowledge store. |
| Mode | Ambient / Solo / Social / Lecture / Wind-down. |
| Girl mode | Trans-flag orb state, auto-triggered on feminine/personal context. |
| Scene | One keyword that raises a whole configured workflow (e.g. 'LSB' → record + transcribe + note template). |
| Trigger | A `Ciel-...:` marker in a note that invokes a vault action. |
| Brain | The always-on PC backend. |
| Client | Tablet or phone app. |
| Command set | The fixed allow-list of actions the executor may run. |
| SNN | Spiking neural network — event-driven, low-power local model. |
| LSB | Case-based learning sessions in the UiO medicine programme. |
| Dr. Katchi | How Ciel addresses the user: Katchi Senthil Ganesh. |
