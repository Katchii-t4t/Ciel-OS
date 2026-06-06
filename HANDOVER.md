# Project Ciel — Handover

_Last updated: 2026-06-07 (post late-night wallpaper session). For Katchi, and for any
fresh Claude Code session picking this up._

---

## 0. TL;DR — where we are right now

Ciel is a JARVIS-like ambient assistant: a **PC FastAPI brain** + a **Flutter Android
launcher** (`ciel_app`) on a **Samsung Galaxy Tab S10+**, backed by the Claude API. It
reads Katchi's Obsidian vault (Nynorsk notes), answers in **English** (text + British
voice), launches apps from S Pen handwriting, floats a corner orb over other apps,
auto-shifts colour by topic, and shows a **live, orbiting "Ciel orb" wallpaper**.

**Phases 0, 1, 2, 4 = COMPLETE. Phase 3 (Voice) = mostly done (3.1 + 3.3 + English
switch). Pending: 3.2 ElevenLabs voice, 3.4 wake word.**

### The single open thread (lock-screen wallpaper)
- ✅ **Home/system wallpaper is the LIVE moving orb** — confirmed via
  `dumpsys wallpaper` → `mWallpaperComponent = com.example.ciel_app/.CielWallpaperService`.
  It persists; it does not revert on its own.
- ❌ **Lock screen still shows a STATIC orb** — a leftover `FLAG_LOCK` override
  (`ImageWallpaper`) sits on top of the live one.
- ✅ **Fix committed + pushed** (`1fe90e5`): on every app resume, `_ensureWallpaper()`
  clears the static lock override **only when** the live Ciel wallpaper is the active
  system wallpaper (guarded, so the lock never collapses to blank).
- ⚠️ **Not yet deployed** because reinstalling the APK resets the live wallpaper to
  default (Android kills the WallpaperService on package replace), and the device was
  **securely locked** so it couldn't be triggered remotely.

**The one manual step left (no reinstall needed):**
> Ciel → settings (gear) → **"Sett LEVANDE Ciel-bakgrunn (orbit)"** → **Set wallpaper**
> → **Home and lock screen**.

If the lock animates after that → done. If One UI only applies live to home and forces
the lock to a static image (a real possibility on Samsung), that's a hardware/OS limit no
code can override — the static orb is then the best the lock can do, while home stays live.

---

## 1. Repo & machine

- **Repo:** `C:\Users\sgkar\ciel` → GitHub `Katchii-t4t/Ciel-OS` (branch `main`).
  Latest commit at handover: **`1fe90e5`**.
- **Backend:** `ciel_server.py` (FastAPI, port 8765). Runs hidden on PC; key from User env.
- **Flutter app:** `ciel_app/` (pkg `com.example.ciel_app`, label "Ciel").
- **PC IP:** `192.168.10.194:8765` (default server URL baked into the app).
- **Tablet:** Galaxy Tab S10+, adb serial `R5GYC3QJYJY`.
- **Flutter:** 3.44.1 at `C:\Users\sgkar\flutter`. **JDK:** Temurin 17. **Android SDK:**
  `%LOCALAPPDATA%\Android\Sdk`.

### Commands you always need
```powershell
# adb (refresh PATH in a new shell):
$adb = "$env:LOCALAPPDATA\Android\Sdk\platform-tools\adb.exe"
$id  = "R5GYC3QJYJY"

# Load the API key into a new terminal (NEVER hardcode it):
$env:ANTHROPIC_API_KEY = [System.Environment]::GetEnvironmentVariable("ANTHROPIC_API_KEY","User")

# Start the server (from C:\Users\sgkar\ciel):
python ciel_server.py            # -> http://0.0.0.0:8765  (docs at /docs)

# Build + deploy the app (release; minify MUST stay OFF):
flutter build apk --release
& $adb -s $id install -r build\app\outputs\flutter-apk\app-release.apk
```

---

## 2. What works (verified on device)

| Area | Status | Notes |
|---|---|---|
| FastAPI brain | ✅ | REST + 2 WebSockets; Haiku/Sonnet routing; allow-listed commands; action log |
| Vault reading | ✅ | Reads Nynorsk notes; path-traversal blocked |
| Flutter client | ✅ | Orb UI (gold + trans "girl mode"); online over LAN |
| Launcher (home) | ✅ | HOME intent; revert via Settings→Default apps→Home |
| S Pen → action | ✅ (Katchi-tested) | ML Kit Digital Ink; opens apps by name; scene words set mode |
| Corner overlay orb | ✅ | flutter_overlay_window; tap → back to Ciel (needs battery=Unrestricted) |
| Auto colour/girl-mode | ✅ | Server classifies topic → broadcasts over /ws/events |
| Voice OUT (TTS) | ✅ | flutter_tts, en-GB, rate 0.45; speaks answers + welcome |
| Voice IN (STT) | ✅ (server-verified) | /api/transcribe → NB-Whisper (nb-whisper-medium, CPU, forced NO) |
| English answers | ✅ | Server prompts answer in English; voice en-GB; notes stay Nynorsk |
| Welcome gate (experience) | ✅ | Pen passphrase / fingerprint / FACE via local_auth (NOT real security) |
| Live HOME wallpaper | ✅ | Orbiting orb (CielWallpaperService) |
| Live LOCK wallpaper | ⚠️ | Static override on top; see §0 — one manual picker step |

---

## 3. Key files

**Backend**
- `ciel_server.py` — FastAPI. `build_general_prompt` / `build_deep_prompt` (English answers),
  `/api/transcribe` (lazy `_get_whisper()`), girl-mode classifier + /ws/events broadcast.

**Flutter (`ciel_app/lib/`)**
- `screens/home.dart` — main UI. Voice in/out, mic record→transcribe→ask, greeting,
  `_ensureWallpaper()` (lock self-heal, guarded), lifecycle resume hooks, settings sheet.
- `services/voice.dart` — FlutterTts wrapper (en-GB).
- `services/launcher.dart` — MethodChannel `ciel/launcher`: launchApp, listApps,
  setLockWallpaper, openLiveWallpaper, liveWallpaperPkg, clearLockWallpaper.
- `services/ciel_api.dart` — REST + WS; `transcribe(wavBytes)` multipart → /api/transcribe.
- `widgets/orb.dart` — CielOrb painter + `renderOrbPng` (static star-field, manual button only).

**Android (`ciel_app/android/app/src/main/kotlin/com/example/ciel_app/`)**
- `MainActivity.kt` — FlutterFragmentActivity; MethodChannel handlers (fuzzy app match;
  setLockWallpaper sets FLAG_SYSTEM + FLAG_LOCK **separately**; clearLockWallpaper =
  `WallpaperManager.clear(FLAG_LOCK)`; openLiveWallpaper = ACTION_CHANGE_LIVE_WALLPAPER).
- `CielWallpaperService.kt` — the live wallpaper: ~320 particles orbit the core to the
  screen edges, trans/gold (reads `flutter.girl_permanent`), rays + aura, onZoomChanged morph.
- `AndroidManifest.xml` — HOME intent, INTERNET, SYSTEM_ALERT_WINDOW,
  FOREGROUND_SERVICE_SPECIAL_USE, USE_BIOMETRIC, RECORD_AUDIO, SET_WALLPAPER; declares
  OverlayService + CielWallpaperService; LAUNCHER queries.
- `build.gradle.kts` — **isMinifyEnabled=false, isShrinkResources=false (MUST stay)**.

---

## 4. Gotchas / hard-won lessons (don't relearn these)

1. **R8/minify MUST stay OFF for release** (`build.gradle.kts`). R8 strips
   WorkManager/Room that ML Kit digital-ink needs → "Failed to create WorkDatabase"
   crash-loop. Dart AOT perf is unaffected.
2. **Reinstall / force-stop / crash-loop all RESET the live wallpaper** to Samsung
   default (the WallpaperService is in the same package). Re-set it via the system
   picker afterward. So **don't reinstall casually** when the live wallpaper is set.
3. **Setting a live wallpaper needs a human tap** in the system picker. `am start` the
   livepicker + `adb input tap` is unreliable (misses constantly in landscape; only
   semi-works after `settings put system user_rotation 0`). Treat it as a manual step.
4. **`cmd wallpaper` shell only does dimming** — there is NO adb command to clear/set the
   lock wallpaper. `service call wallpaper <code>` marshalling is too fragile; don't.
5. **Can't reach a securely-locked device remotely** (`deviceLocked=1`). Anything needing
   the app foreground or the lock screen must wait for Katchi to unlock.
6. **setLockWallpaper: set FLAG_SYSTEM and FLAG_LOCK in two separate calls** — the
   combined flag fails on Samsung.
7. **Don't re-add `setShowWhenLocked`/`setTurnScreenOn`.** It occluded the secure
   keyguard → device stayed locked → opening apps popped the keyguard (felt buggy). Ciel
   is the home screen AFTER a normal unlock; the fingerprint/face is the real secure layer.
8. **Samsung Freecess freezes backgrounded apps** → set Ciel battery to **Unrestricted**
   for the corner-orb tap-to-home to work reliably. (Still pending Katchi's tap.)
9. **GoodNotes is a TWA** (`com.goodnotes.android.app`) opening via Samsung Internet
   custom tab; app-name matching is normalized (lowercase/alnum) so "good notes" → GoodNotes.
10. **Can't change the system lock LAYOUT** (clock/widgets are Samsung SystemUI). Only the
    wallpaper is ours. Katchi customises clock/widgets in One UI lock settings herself.

### Security rules (non-negotiable)
- **Never hardcode or paste `ANTHROPIC_API_KEY`.** Load it from the User env var only.
- Server commands are a fixed allow-list; path-traversal is blocked; actions are logged.
- Be careful with the tablet — it's Katchi's daily-driver. Minimise poking it while she's
  actively using an app (e.g. studying in GoodNotes).

---

## 5. Pending / next

- **Finish the lock wallpaper** (see §0) — one picker step from Katchi, then verify motion.
- **Phase 3.2 — ElevenLabs premium voice** (server-side TTS). Needs Katchi's ElevenLabs
  key + a cost OK. Quick win already done = flutter_tts; this is the "proper" voice.
- **Phase 3.4 — wake word** ("Ciel ...") + fuller spoken welcome ritual.
- **Katchi's tap:** Ciel → Battery → **Unrestricted**.
- **Future (Phase 7, SPEC Module I+L):** periodic screen capture → OCR/analyse → discreet
  suggestions via the corner orb. Honest constraints noted in `project_known_issues.md` #10
  (Android forces a visible capture indicator; Vision is costly → cheap local OCR first,
  on-demand, cost-capped).
- **Phases 5–9 (roadmap):** proactive tracker, lecture assist, music, SNN, glasses.

---

## 6. Working with Katchi (style)

- Medicine + maths student, UiO. Pronouns **ho/hennar**. Writes **Nynorsk**, speaks
  English. Ciel itself is English; her notes stay Nynorsk.
- Likes **autonomy + momentum** — "do as much as possible, but do it well and precise."
- Gets (rightly) frustrated by repeated "it's fixed" that then reverts, and by the tablet
  being poked mid-study. **Be honest about real limits** (Android/Samsung walls) instead
  of over-promising. When something genuinely needs her hands (a picker tap, an unlock),
  say so plainly and make it one clear step.
