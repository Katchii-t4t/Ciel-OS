"""
ciel_proactive.py — Fase 5: Proaktiv motor + livssporing (Module F + J)
=======================================================================
Server-delen av Fase 5. Rein og fjernbar: ciel_server.py importerer denne, men
Ciel fungerer identisk om fila er borte (endepunkta fell tilbake til stub).

To ting:
  • daily_score()  — gjennomsiktig dagsscore (Module J). Config-styrte vekter.
    Velvære-vakt (SPEC §10): kvile er ein POSITIV metrikk, ingen restriksjons-
    rammar, og ein låg dag gir éin mild prioritet — aldri ei lekse.
  • briefing()     — proaktiv morgon/kveld-oppsummering (Module F), klar til å
    lesast høgt av orben.

ÆRLEGDOM: scoren byggjer berre på signal vi FAKTISK har på PC-en (vault-
aktivitet). Søvn/trening/HRT (Health Connect, Module J) er ikkje kopla server-
side enno — dei vert lista som "ikkje tilkopla", aldri gjetta eller fabrikkert.
"""

from __future__ import annotations

import os
from datetime import date, datetime, timezone
from stc_agent import VAULT, IGNORE

# Faste tider for proaktiv levering (lokal tid). Overstyrbart med miljøvariablar.
MORNING_HOUR = int(os.environ.get("CIEL_MORNING_HOUR", "7"))   # morgonbriefing frå kl. 07
EVENING_HOUR = int(os.environ.get("CIEL_EVENING_HOUR", "21"))  # kveldsbriefing frå kl. 21
MORNING_WINDOW = 4   # morgonbriefing kan framleis leverast inntil 4 t etter (om du sov)


# ── Config: gjennomsiktige vekter (summerer til 1.0) ─────────────────────────
# Endre desse fritt — scoren forklarar alltid kvar poenga kom frå.
WEIGHTS = {
    "study_today":  0.40,   # skreiv/rørte du notat i dag?
    "week_rhythm":  0.30,   # jamn aktivitet siste veka
    "review_health":0.30,   # held du etterslepet av gløymde notat nede?
}

# Signal vi enno IKKJE har server-side (kjem med Health Connect på tabletten)
SIGNALS_PENDING = ["søvn", "trening", "HRT-fase", "skjermtid"]


def _vault_signals() -> dict:
    """Tel vault-aktivitet: i dag, siste veka, og gløymt-etterslep (30+ dagar)."""
    now        = datetime.now()
    today0     = datetime(now.year, now.month, now.day).timestamp()
    week_ago   = now.timestamp() - 7  * 24 * 3600
    month_ago  = now.timestamp() - 30 * 24 * 3600

    today_notes, week_notes, forgotten = [], [], []
    total = 0
    for p in VAULT.rglob("*.md"):
        if any(d in p.parts for d in IGNORE):
            continue
        if p.name.startswith("_"):
            continue
        try:
            st = p.stat()
        except Exception:
            continue
        total += 1
        if st.st_mtime >= today0:
            today_notes.append(p.stem)
        if st.st_mtime >= week_ago:
            week_notes.append(p.stem)
        if st.st_mtime < month_ago and st.st_size > 200:
            forgotten.append(p.stem)

    return {
        "total": total,
        "today": today_notes,
        "week": week_notes,
        "forgotten": forgotten,
    }


def daily_score() -> dict:
    """Gjennomsiktig dagsscore med velvære-vakt. Deterministisk (ingen LLM-kall)."""
    sig = _vault_signals()

    n_today = len(sig["today"])
    n_week  = len(set(sig["week"]))
    n_forgot = len(sig["forgotten"])

    # Kvar komponent → 0..1, så vekta. Forklart i `components` for full openheit.
    study_today   = 1.0 if n_today >= 2 else (0.5 if n_today == 1 else 0.0)
    week_rhythm   = min(1.0, n_week / 7.0)          # 7+ aktive notat = full rytme
    review_health = max(0.0, 1.0 - n_forgot / 20.0) # 0 gløymde = 1.0, 20+ = 0.0

    parts = {
        "study_today":   study_today,
        "week_rhythm":   week_rhythm,
        "review_health": review_health,
    }
    score = round(100 * sum(parts[k] * WEIGHTS[k] for k in WEIGHTS))

    components = [
        {"label": "Studieaktivitet i dag", "value": f"{n_today} notat",
         "weight": WEIGHTS["study_today"],  "points": round(100 * study_today * WEIGHTS["study_today"])},
        {"label": "Rytme siste veka", "value": f"{n_week} aktive notat",
         "weight": WEIGHTS["week_rhythm"],  "points": round(100 * week_rhythm * WEIGHTS["week_rhythm"])},
        {"label": "Repetisjon (etterslep)", "value": f"{n_forgot} gløymde",
         "weight": WEIGHTS["review_health"],"points": round(100 * review_health * WEIGHTS["review_health"])},
    ]

    # Éin høgaste-effekt prioritet — mild, aldri ei lekse (velvære-vakt).
    if n_today == 0 and n_week == 0:
        priority = "Kvil i dag om du treng det — ingen notat er rørt, og det er heilt greitt. Eitt lite steg held."
    elif n_forgot >= 10:
        eldste = sig["forgotten"][0]
        priority = f"Du har {n_forgot} notat du ikkje har sett på lenge. Ta éitt — t.d. «{eldste}» — så er etterslepet mindre skummelt."
    elif n_today == 0:
        priority = "Du har vore aktiv i veka, men ikkje i dag. Tjue minutt på eitt tema er nok til å halde rytmen."
    else:
        priority = f"God rytme. Bygg vidare på det du skreiv i dag ({sig['today'][0]}) medan det er ferskt."

    return {
        "date": date.today().isoformat(),
        "score": score,
        "components": components,
        "priority": priority,
        "wellbeing_note": "Kvile er ein positiv metrikk. Ein låg dag er data, ikkje ein dom.",
        "signals_connected": ["vault-aktivitet"],
        "signals_pending": SIGNALS_PENDING,
    }


def briefing(kind: str, complete, model: str) -> dict:
    """Proaktiv morgon/kveld-briefing, klar til å lesast høgt av orben (Module F).
    `complete(prompt, model, max_tokens)` vert sendt inn frå serveren."""
    kind = (kind or "morning").lower()
    sig  = _vault_signals()
    sc   = daily_score()

    siste = ", ".join(sig["today"][:5]) or "ingen i dag"
    veka  = ", ".join(list(dict.fromkeys(sig["week"]))[:6]) or "roleg veke"
    glo   = ", ".join(sig["forgotten"][:3]) or "ingen"

    when = "morgon" if kind == "morning" else "kveld"
    tone = ("kort, varm og motiverande — set tonen for dagen"
            if kind == "morning" else
            "roleg og avrundande — hjelp henne lande dagen")

    prompt = f"""Du er Ciel, den personlege assistenten til Dr. Katchi (ho/hennar), medisin- og matematikkstudent ved UiO.

Lag ein {when}s-briefing. {tone}. Den skal LESAST HØGT, så skriv naturleg tale på engelsk (Ciel snakkar engelsk), 3–4 korte setningar, ingen punktlister, ingen markdown.

Det du veit akkurat no:
- Notat rørt i dag: {siste}
- Aktive tema siste veka: {veka}
- Notat ho ikkje har sett på lenge: {glo}
- Dagsscore: {sc['score']}/100 — prioritet: {sc['priority']}

Tiltal henne som "Dr. Katchi". Vær konkret om hennar eigne tema. Aldri masande; kvile er greitt. Ikkje finn på fakta du ikkje har."""

    try:
        text = complete(prompt, model, 350).strip()
    except Exception as e:
        text = f"(Briefing utilgjengeleg — kunne ikkje nå språkmodellen: {e})"

    return {"kind": kind, "date": date.today().isoformat(), "text": text, "score": sc["score"]}


def due_events(now: datetime | None = None, already_fired: set[str] | None = None) -> list[dict]:
    """Rein funksjon (Module F): kva proaktive hendingar er due NO?
    Serveren held styr på kva som alt er levert i dag (`already_fired`), så
    same briefing ikkje kjem to gonger. Testbar når som helst med eit gjeve `now`."""
    now = now or datetime.now()
    fired = already_fired or set()
    h = now.hour
    due: list[dict] = []

    if "morning" not in fired and MORNING_HOUR <= h < MORNING_HOUR + MORNING_WINDOW:
        due.append({"kind": "morning", "reason": "morgonbriefing"})

    if "evening" not in fired and h >= EVENING_HOUR:
        due.append({"kind": "evening", "reason": "kveldsbriefing"})

    return due


# ── Sjølvtest: `python ciel_proactive.py` ────────────────────────────────────
if __name__ == "__main__":
    import sys
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sc = daily_score()
    print(f"\nDagsscore: {sc['score']}/100")
    for c in sc["components"]:
        print(f"  • {c['label']}: {c['value']}  → {c['points']} poeng (vekt {c['weight']})")
    print(f"  Prioritet: {sc['priority']}")
    print(f"  Ikkje tilkopla enno: {', '.join(sc['signals_pending'])}")

    print("\nProaktiv planleggjar (kva er due til ulike tider):")
    for hh in (6, 8, 14, 21, 23):
        t = datetime.now().replace(hour=hh, minute=0)
        evs = [e["kind"] for e in due_events(t)]
        print(f"  kl. {hh:02d}:00 → {evs or 'ingenting'}")

