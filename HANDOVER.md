# Project Ciel — Full Handover

_Last updated: 2026-06-07 morning. Written for a fresh Claude Code session picking this
up cold. Read top to bottom before touching anything._

---

## 0. What is Ciel?

Ciel is a personal AI operating system built for **Katchi** (ho/hennar) — a medicine +
maths student at UiO. The vision: JARVIS, but real, private, and built on 2026 consumer
hardware. The assistant IS the interface — a breathing orb replaces the Android home
screen. You write with the S Pen, speak aloud, or tap the orb, and whole workflows
surface.

**Stack:**
- **PC brain:** Python + FastAPI server (`ciel_server.py`) on Katchi's Windows PC,
  backed by the Anthropic Claude API (Haiku for speed, Sonnet for depth).
- **Tablet client:** Flutter app (`ciel_app`) on a Samsung Galaxy Tab S10+. This IS the
  home screen (Android launcher).
- **Vault:** Katchi's Obsidian notes (Nynorsk). Ciel reads them and answers in English.
- **Voice:** NB-Whisper (local, on PC) for speech-to-text; flutter_tts (local, on tablet)
  for voice output.

**GitHub:** `Katchii-t4t/Ciel-OS` (branch `main`). Local: `C:\Users\sgkar\ciel`.
**Latest commit at handover: `973451e`** (the previous HANDOVER.md).

---

## 1. Current state (read this first)

### What works right now (verified on device)

| Feature | Status | Verified how |
|---|---|---|
| FastAPI brain, Claude routing | ✅ | Live API calls, real answers |
| Vault reading (Nynorsk notes) | ✅ | Real vault path, real notes |
| Flutter orb UI on tablet | ✅ | Screenshot + device |
| Ciel is the Android home screen | ✅ | HOME intent, boot-persists |
| S Pen handwriting → open app / ask Ciel | ✅ | Katchi tested with real S Pen |
| Corner orb overlay over other apps | ✅ | flutter_overlay_window |
| Auto colour shift by topic (girl mode) | ✅ | Server classifies → WS broadcast |
| Ciel speaks answers aloud (TTS) | ✅ | Google TTS plays en-GB |
| Spoken welcome on launch | ✅ | "Good morning/evening, Dr. Katchi" |
| Voice input (mic → NB-Whisper → text) | ✅ | Server 200 OK; live mic = Katchi's test |
| English answers (Nynorsk notes ok) | ✅ | Real answer confirmed |
| Ciel welcome gate (pen/fingerprint/face) | ✅ | All 3 paths confirmed |
| Girl mode permanent (trans orb, default on) | ✅ | SharedPrefs `girl_permanent=true` |
| Live HOME wallpaper (moving orb) | ✅ | `dumpsys` confirms CielWallpaperService |
| Live LOCK wallpaper (moving orb on lock) | ⚠️ | One manual step left — see §2 |

### The one open thread: lock-screen wallpaper

The **home screen** has the live, orbiting Ciel orb — confirmed by `dumpsys wallpaper`:
```
mWallpaperComponent=com.example.ciel_app/com.example.ciel_app.CielWallpaperService
```
This persists and does not revert on its own.

The **lock screen** still has a leftover static `ImageWallpaper` override sitting on top
of the live orb. The live orb is underneath — it just can't be seen because the static
layer blocks it.

**The fix is committed** (`1fe90e5`): on every app resume, `_ensureWallpaper()` calls
`WallpaperManager.clear(FLAG_LOCK)` — but only when the live Ciel wallpaper is
confirmed as the active system wallpaper (so the lock never collapses to blank).

**This fix is NOT yet deployed** — reinstalling the APK kills the WallpaperService and
resets the live wallpaper to the Samsung default. So I deliberately did NOT reinstall
(left the live home orb alive).

**The one manual step (no reinstall):**
> Open Ciel → tap the gear icon → **"Sett LEVANDE Ciel-bakgrunn (orbit)"** →
> in the system preview → **Set wallpaper** → **Home and lock screen**

If the lock animates afterward → done forever (code keeps it that way on every unlock).
If Samsung forces lock=static (possible on One UI) → that's a hardware/OS limit, no code
can override it. The static orb is then the best the lock can do.

**Do NOT** force-stop, reinstall, or reboot unless you're ready to redo the picker step.

---

## 2. Machine setup

| Thing | Value |
|---|---|
| PC username | `sgkar` (Windows) |
| PC local IP | `192.168.10.194` |
| Server port | `8765` |
| Tablet | Samsung Galaxy Tab S10+ |
| Tablet adb serial | `R5GYC3QJYJY` |
| Tablet IP (WiFi) | `192.168.10.166` |
| Flutter | 3.44.1 at `C:\Users\sgkar\flutter` |
| JDK | Temurin 17 at `C:\Program Files\Eclipse Adoptium\jdk-17.0.19.10-hotspot` |
| Android SDK | `%LOCALAPPDATA%\Android\Sdk` (platform-36, build-tools 36.0.0) |
| Python env (with all deps) | `C:\Users\sgkar\anaconda3\python.exe` |
| Obsidian vault | `C:\Users\sgkar\OneDrive\Documents\ObsidianVault` (or similar — server reads from `CIEL_VAULT` env var or auto-detects) |
| API key | Windows User env var `ANTHROPIC_API_KEY` — never hardcode, never paste |

### Essential PowerShell snippets (run at start of every session)

```powershell
# 1. Load adb
$adb = "$env:LOCALAPPDATA\Android\Sdk\platform-tools\adb.exe"
$id  = "R5GYC3QJYJY"

# 2. Load API key into current shell (NEVER hardcode)
$env:ANTHROPIC_API_KEY = [System.Environment]::GetEnvironmentVariable("ANTHROPIC_API_KEY","User")
$env:KMP_DUPLICATE_LIB_OK = "TRUE"     # required for PyTorch/NB-Whisper on Windows

# 3. Start the brain (from C:\Users\sgkar\ciel)
cd C:\Users\sgkar\ciel
Start-Process -FilePath "C:\Users\sgkar\anaconda3\python.exe" `
  -ArgumentList "ciel_server.py" -WorkingDirectory "C:\Users\sgkar\ciel" -WindowStyle Hidden

# 4. Verify it's alive
Invoke-WebRequest -Uri "http://127.0.0.1:8765/health" -UseBasicParsing

# 5. Check tablet is connected
& $adb devices
```

### Build + deploy app (IMPORTANT rules)
```powershell
cd C:\Users\sgkar\ciel\ciel_app
flutter build apk --release        # minify MUST stay OFF — see gotcha #1

& $adb -s $id install -r build\app\outputs\flutter-apk\app-release.apk
# WARNING: installing resets the live wallpaper to Samsung default.
# After installing: redo the live wallpaper picker step (Ciel gear → Sett LEVANDE...).
```

---

## 3. Codebase map

```
ciel/
├── ciel_server.py          ← FastAPI brain (THE server — start this first)
├── start_ciel.vbs          ← legacy startup for Phase-0 vault agents (not the server)
├── requirements.txt
├── HANDOVER.md             ← this file
├── logs/
│   └── action_log.jsonl    ← every POST /api/command logged here
└── ciel_app/               ← Flutter Android app
    ├── lib/
    │   ├── main.dart               ← CielRoot: gate → home; handles overlay share
    │   ├── screens/
    │   │   ├── home.dart           ← THE main UI (big file, read carefully)
    │   │   └── lock_gate.dart      ← Ciel welcome gate (pen/biometric)
    │   ├── services/
    │   │   ├── ciel_api.dart       ← REST + WebSocket client; transcribe()
    │   │   ├── launcher.dart       ← MethodChannel bridge to Kotlin
    │   │   ├── voice.dart          ← flutter_tts wrapper (en-GB)
    │   │   └── lock.dart           ← gate unlock logic + SharedPrefs
    │   └── widgets/
    │       ├── orb.dart            ← CielOrb CustomPainter + renderOrbPng()
    │       └── handwriting.dart    ← InkLayer: S Pen ML Kit recognition
    └── android/app/src/main/
        ├── kotlin/com/example/ciel_app/
        │   ├── MainActivity.kt         ← FlutterFragmentActivity + MethodChannel
        │   └── CielWallpaperService.kt ← live wallpaper (320 particles, trans/gold)
        └── AndroidManifest.xml
```

### `ciel_server.py` — key internals
- **LLM routing:** `classify_depth(question)` → Haiku (simple) or Sonnet (deep).
- **Prompts:** `build_general_prompt()` and `build_deep_prompt()` — both instruct Claude
  to **answer in English**, read Nynorsk notes fine. Max 300 words, no markdown headers.
- **`/api/transcribe`:** lazy-loads NB-Whisper (`NbAiLab/nb-whisper-medium`, CPU, forced
  `language="no"`, `task="transcribe"`). Reads WAV via `soundfile`, chunk 30s, batch 4.
  Lazy = server boots fast, model loads on first voice request (~30s first time).
- **Girl-mode auto:** `GIRL_TRIGGERS` keyword set → `classify_girl_mode()` →
  `_maybe_girl_mode()` broadcasts `{"type":"girl_mode","active":true}` over `/ws/events`.
- **Security:** allow-listed commands (`set_mode`, `set_girl_mode`, `open_note`,
  `search_vault`); path-traversal blocked; all actions logged to `logs/action_log.jsonl`.
- **Env vars:** `ANTHROPIC_API_KEY` (required), `CIEL_WHISPER` (model override),
  `CIEL_MODEL_SIMPLE`/`CIEL_MODEL_DEEP` (LLM override), `CIEL_VAULT` (vault path).

### `home.dart` — key internals
- **Voice out:** `final Voice _voice`. `_boot()` inits + speaks greeting if `_voiceOn`.
  `_ask()` onDone speaks the answer. Settings toggle "Stemme — les svar høgt".
- **Voice in:** `final AudioRecorder _rec`. `_toggleRecord()`: record WAV 16kHz mono →
  `_api.transcribe(bytes)` → fills `_input.text` → auto-calls `_ask()`.
- **Greeting:** `_greetingText()` → `"Good morning/afternoon/evening, Dr. Katchi"`.
- **Wallpaper self-heal:** `_ensureWallpaper()`: calls `Launcher.liveWallpaperPkg()` →
  if it contains `ciel_app` → `Launcher.clearLockWallpaper()`. Called on cold start AND
  every `didChangeAppLifecycleState(resumed)`. **Never sets a static image automatically.**
- **Girl mode:** `_girlPermanent` (default `true`). Orb shows trans-flag always; auto
  topic-based detection also works when permanent is off.

### `CielWallpaperService.kt` — live wallpaper
- ~320 particles orbit the orb core out to screen edges, like a solar system.
- Colours: trans-flag (blue/pink/white) when `flutter.girl_permanent == true`; gold otherwise.
- Rays + aura around core. `onZoomChanged`: particles morph inward on the unlock swipe.
- Applied via system picker — cannot be set programmatically without the picker tap.

### `MainActivity.kt` — MethodChannel handlers
| Method | What it does |
|---|---|
| `launchApp` | Fuzzy-matches query (normalized alnum) against all launchable apps; opens best match |
| `listApps` | Returns all launchable app labels |
| `setLockWallpaper` | Sets PNG bytes as FLAG_SYSTEM **then** FLAG_LOCK (two separate calls — combined fails on Samsung) |
| `openLiveWallpaper` | Fires `ACTION_CHANGE_LIVE_WALLPAPER` intent pointing at CielWallpaperService |
| `liveWallpaperPkg` | Returns `wallpaperInfo?.packageName` (null if static) |
| `clearLockWallpaper` | `WallpaperManager.clear(FLAG_LOCK)` — removes static lock override |

---

## 4. What each phase built (full history)

### Phase 0 — Vault agents (complete, pre-session)
- `stc_agent.py`: watches Obsidian vault every 3s; `Ciel: "question"` → AI answer inline.
- `stc_pdf.py`: auto-imports lecture PDFs.
- `stc_lyd.py`: NB-Whisper lecture transcription → structured Nynorsk notes.
- Started via `start_ciel.vbs` (legacy; NOT the FastAPI server).

### Phase 1 — FastAPI brain (complete, commit `8450e7c` → pushed)
- Full REST + WebSocket API. Smart LLM routing. Vault search. Security (allow-list,
  path-traversal block, action log). `requirements.txt`. README.

### Phase 2 — Flutter client (complete, commits through `f590b8c`)
- Orb UI (CustomPainter port of `ciel_orb_v3.html`). REST+WS client. LAN connection.
- Full Android toolchain set up on PC: Temurin JDK, Android SDK, `flutter config`.
- Deployed to Tab S10+ via ADB. End-to-end verified (tablet → PC → Claude → answer).

### Phase 3 — Voice (mostly complete)
- **3.1 ✅:** Ciel speaks answers. `voice.dart` (flutter_tts, en-GB, rate 0.45).
  Toggle in settings. Commit `e4a9006`.
- **3.2 ⏳ PENDING:** ElevenLabs premium voice. Needs Katchi's ElevenLabs API key +
  cost decision. The local flutter_tts works; this is the "proper JARVIS" voice.
- **3.3 ✅:** Voice input. Mic button → WAV 16kHz → `POST /api/transcribe` →
  NB-Whisper on PC → text → auto-asks. Commit `a40c1b0`.
- **3.4 ⏳ PENDING:** Wake word ("Hey Ciel"). Always-listening service. Deferred
  because Samsung Freecess + battery management makes background services fragile.

### Phase 4 — Launcher + ambient OS (complete, commits through `4ea8bbc`)
- **Launcher:** Ciel IS the home screen (HOME intent, `FlutterFragmentActivity`, edge-to-edge).
- **S Pen handwriting → action:** `handwriting.dart` (InkLayer, stylus-only strokes,
  ML Kit Digital Ink local recognition). After recognition pause: app name → launch,
  scene word (lsb/forelesing/studie/sjakk) → set mode, else → ask Ciel.
- **Corner orb overlay:** `flutter_overlay_window`. Small orb floats over all other apps.
  Tap → returns to Ciel. Needs `SYSTEM_ALERT_WINDOW` (grantable via adb).
- **Auto colour/girl-mode:** server classifies topic keywords → broadcasts over `/ws/events`
  → orb glides between trans-flag and gold colours.
- **Welcome gate:** `lock_gate.dart`. Pen passphrase (ML Kit + sha256) OR fingerprint +
  face (local_auth BiometricPrompt). Off by default; toggle in settings (long-press orb).
  **NOT real device security** — this is an experience layer on top of Android's real lock.
- **Live wallpaper:** `CielWallpaperService.kt`. 320 orbiting particles, trans/gold, rays.

### Polish + fixes (through this session)
- Custom app icon.
- Lock screen: removed `setShowWhenLocked`/`setTurnScreenOn` (caused half-locked state).
- English switch: server prompts → English, TTS → en-GB, greeting → English.
  Katchi's notes stay Nynorsk; Ciel reads them and answers in English.
- Wallpaper self-heal: rewrote multiple times. Final correct version = never set static
  automatically; only clear the static lock override; guarded by liveWallpaperPkg check.
- GoodNotes launch fixed: normalized alnum matching so "good notes" → GoodNotes (TWA).
- R8 minify disabled (see gotcha #1).

---

## 5. Gotchas — do not relearn these

1. **R8/minify MUST stay OFF.** `build.gradle.kts`: `isMinifyEnabled=false`,
   `isShrinkResources=false`. R8 strips WorkManager/Room that ML Kit needs →
   "Failed to create WorkDatabase" crash-loop on launch. Dart AOT is unaffected.
   **Never turn this back on.**

2. **Reinstall / force-stop / crash-loop all reset the live wallpaper** to Samsung
   default. Android kills the WallpaperService on package replace. After any reinstall
   you MUST redo the live wallpaper picker step.

3. **Setting a live wallpaper requires a human tap** in the system picker. `am start
   com.android.wallpaper.livepicker/.LiveWallpaperChange` then `adb input tap` is
   unreliable — misses constantly in landscape. Only semi-works after forcing portrait
   (`adb shell settings put system user_rotation 0`). Always treat it as Katchi's manual step.

4. **`cmd wallpaper` shell only does dimming** — no adb route to clear/set the lock
   wallpaper layer. `service call wallpaper` marshalling is too fragile. Don't try.

5. **Can't do anything on a securely-locked device remotely.** `deviceLocked=1` means
   no access to the app foreground or picker. Wait for Katchi to unlock.

6. **setLockWallpaper: two separate calls, not combined.** `FLAG_SYSTEM or FLAG_LOCK`
   as a combined flag fails silently on Samsung. Call `setBitmap(..., FLAG_SYSTEM)` then
   `setBitmap(..., FLAG_LOCK)` separately.

7. **Do NOT re-add `setShowWhenLocked`/`setTurnScreenOn`.** Tried and removed. It made
   Ciel show over a still-locked device → opening any app popped the keyguard → felt
   broken. Ciel is the home screen AFTER a real unlock (fingerprint/face). Leave it.

8. **Samsung Freecess freezes backgrounded apps** when battery-optimised. Corner-orb
   tap-to-home is unreliable until Katchi sets Ciel → Battery → **Unrestricted**
   (still a pending Katchi action).

9. **GoodNotes is a TWA** (com.goodnotes.android.app). It opens via Samsung Internet
   custom tab. Handwriting recognition writes "good notes" (two words) → normalized
   matching handles it.

10. **Can't change the system lock LAYOUT** (clock position, widgets). That's Samsung
    SystemUI. Only the wallpaper layer is ours. Katchi customises the clock/widgets
    herself in One UI lock screen settings.

11. **NB-Whisper first load takes ~30 seconds.** Lazy-loaded on first `/api/transcribe`
    request. Server health is fine while the model loads. Tell Katchi to wait on first
    voice use each server restart.

12. **KMP_DUPLICATE_LIB_OK=TRUE** must be set in the environment before importing
    torch on Windows. Already in `start_ciel.vbs`; set manually in new PowerShell
    sessions before starting the server.

13. **local_auth API on this version:** `authenticate(localizedReason: '...', biometricOnly: true)`.
    No `options:` or `stickyAuth` params — not supported in the installed version.

---

## 6. Pending tasks (priority order)

| Priority | Task | Notes |
|---|---|---|
| 🔴 | **Lock wallpaper picker tap** | Katchi does: Ciel gear → "Sett LEVANDE..." → Set wallpaper → Home and lock screen. Verify lock moves. |
| 🔴 | **Ciel battery → Unrestricted** | Katchi does: Settings → Apps → Ciel → Battery → Unrestricted. Fixes corner-orb tap-to-home. |
| 🟡 | **Prompt caching** | Server-side only change. Reduces Claude API cost ~30–50%. No rebuild needed. |
| 🟡 | **Phase 3.2 — ElevenLabs voice** | Needs Katchi's ElevenLabs API key + cost OK ($0 on free tier to test). Server-side TTS → stream audio to tablet. |
| 🟡 | **Phase 3.4 — Wake word** | "Hey Ciel" → hands-free. Background always-listening service. Fragile with Samsung Freecess — build carefully. |
| 🟢 | **On-demand screen suggestions (Phase 7 mini)** | Katchi presses orb → tablet screenshots → local OCR (ML Kit, free) → Claude → corner orb suggestion. No constant capture. |
| 🟢 | **Server auto-start on PC boot** | Update `start_ciel.vbs` to also launch `ciel_server.py` with the right Python + env vars. |
| 🟢 | **Syncthing vault sync** | Currently manual `adb push`. Install Syncthing on tablet → auto-sync vault over WiFi. |
| ⚪ | **Phase 5 — Proactive tracker** | Habit/study plan, "you haven't read today". |
| ⚪ | **Phase 6 — Lecture assistant** | Live transcription → auto structured notes. |
| ⚪ | **Phase 8 — Music** | Ciel controls mood/playlist. |
| ⚪ | **Phase 9 — Glasses/wearables** | Long-term vision. |

---

## 7. Working with Katchi

- **Who:** Medicine + maths student, UiO. Pronouns **ho/hennar**. Writes and speaks
  **Nynorsk** in her own notes. Ciel answers in **English** (her choice).
- **Style:** wants **autonomy and momentum** — "do as much as possible, but do it well
  and precise." Start working immediately; don't ask unnecessary questions.
- **Frustration triggers:**
  - Features that "break" and revert for no apparent reason (especially the wallpaper).
  - Being interrupted mid-study (e.g. GoodNotes active) by unexpected adb taps.
  - Vague answers or over-promising ("it's fixed" then it isn't).
- **What she appreciates:** honesty about real Android/Samsung limits; clear one-step
  instructions when she needs to do something herself; things that *just work*.
- **The tablet is her daily driver.** Be conservative. Don't force-stop, reinstall, or
  run adb taps while she's actively using an app unless explicitly asked.
- **Security:** NEVER hardcode or paste `ANTHROPIC_API_KEY`. Load from Windows User
  env var only. Server commands are allow-listed. Actions are logged.

---

## 8. Quick-start for a fresh session

```powershell
# 1. Load env
$env:ANTHROPIC_API_KEY = [System.Environment]::GetEnvironmentVariable("ANTHROPIC_API_KEY","User")
$env:KMP_DUPLICATE_LIB_OK = "TRUE"
$adb = "$env:LOCALAPPDATA\Android\Sdk\platform-tools\adb.exe"
$id  = "R5GYC3QJYJY"

# 2. Start brain
cd C:\Users\sgkar\ciel
Start-Process "C:\Users\sgkar\anaconda3\python.exe" -ArgumentList "ciel_server.py" `
  -WorkingDirectory "C:\Users\sgkar\ciel" -WindowStyle Hidden
Start-Sleep 8
Invoke-WebRequest http://127.0.0.1:8765/health -UseBasicParsing   # should say {"ok":true}

# 3. Check tablet
& $adb devices

# 4. Read HANDOVER.md (this file), then check project_ciel.md in memory/
```

**Then ask Katchi:** is the home screen orb moving? Is the lock screen orb moving?
Those two questions tell you exactly where you are.
