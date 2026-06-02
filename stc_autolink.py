"""
stc_autolink.py — Automatisk vault-kopling
===========================================
Gjer to ting:

1. EKSPLISITT LENKING
   Finn stader der eit notatnamn er nemnt i teksten utan [[]] rundt
   og legg til lenkene automatisk.
   Døme: "Glykolyse produserer ATP" → "[[Glykolyse]] produserer [[ATP]]"

2. SEMANTISK KOPLING
   Finn notat som handlar om same tema men ikkje lenkar til kvarandre.
   Legg til ei "Relaterte notat"-linje nedst.

Bruk (trygg — gjer ingenting, berre vis kva som ville skjedd):
    python stc_autolink.py

Bruk (skriv endringar til disk):
    python stc_autolink.py --skriv
"""

import re, sys, os
from collections import defaultdict
from pathlib import Path

os.environ.setdefault("PYTHONIOENCODING", "utf-8")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ── Konfigurasjon ──────────────────────────────────────────────────────────────
_parent = Path("C:/Users/Karthik/OneDrive/Obidian stasj")
_match  = [d for d in _parent.iterdir() if "stash" in d.name.lower() and "Copy" not in d.name]
if not _match:
    print("FEIL: Fann ikkje vault-mappa!"); raise SystemExit(1)

VAULT       = _match[0]
IGNORE      = {".obsidian", ".trash", "Usikkere notat ord"}
DRY_RUN     = "--skriv" not in sys.argv
MIN_OVERLAP = 3   # Minimum felles nøkkelord for semantisk kopling
STOPORD     = {"kva","kan","om","er","og","til","frå","fra","med","som","det","dei",
               "har","for","veit","meg","seg","kven","korleis","ein","eit","den",
               "ikkje","enn","men","hva","hvordan","ikke","deg","jeg","min","din",
               "the","and","for","with","this","that","are","from","have","been",
               "will","also","its","not","but","more","than","into","they","which"}

if DRY_RUN:
    print("FØREHANDSVISNING (ingen endringar). Køyr med --skriv for å lagre.\n")
else:
    print("SKRIV-MODUS — gjer endringar i vaulten.\n")

# ── Les alle notat ─────────────────────────────────────────────────────────────
def les_vault():
    notat = {}
    for path in VAULT.rglob("*.md"):
        if any(d in path.parts for d in IGNORE): continue
        if path.name.startswith("_"): continue
        try:
            txt = path.read_text(encoding="utf-8", errors="ignore")
            notat[path] = txt
        except Exception:
            pass
    return notat

# ── Del 1: Eksplisitt lenking ─────────────────────────────────────────────────
def finn_eksisterande_lenker(txt):
    """Finn alle [[lenker]] som allereie finst i teksten."""
    return {m.lower() for m in re.findall(r"\[\[([^\]|]+?)(?:\|[^\]]+?)?\]\]", txt)}

def legg_til_wikilenker(filepath, txt, alle_namn):
    """
    Legg [[]] rundt notatnamn som er nemnt i teksten utan lenke.
    Endrar IKKJE stader som allereie har [[]], frontmatter, eller kodeblokkar.
    """
    # Fjern kodeblokkar og frontmatter frå matching (men behald dei i output)
    eksisterande = finn_eksisterande_lenker(txt)
    ny_txt       = txt
    endringar    = []

    # Sorter etter lengd (lengst fyrst) for å unngå delvis-matching
    for namn in sorted(alle_namn, key=len, reverse=True):
        if namn.lower() == filepath.stem.lower(): continue  # ikkje sjølvlenking
        if namn.lower() in eksisterande: continue           # allereie lenka

        # Match heile ord, ikkje inne i [[]], ikkje inne i backticks
        pattern = r'(?<!\[\[)(?<!\[)(?<!\`)\b(' + re.escape(namn) + r')\b(?!\]\])(?!\`)'
        matches = list(re.finditer(pattern, ny_txt, flags=re.IGNORECASE))

        if matches:
            # Lenk berre FØRSTE førekomst (Obsidian-konvensjon)
            m         = matches[0]
            ny_txt    = ny_txt[:m.start()] + f"[[{m.group(1)}]]" + ny_txt[m.end():]
            endringar.append(namn)
            eksisterande.add(namn.lower())

    return ny_txt, endringar

# ── Del 2: Semantisk kopling ──────────────────────────────────────────────────
def nøkkelord(txt):
    """Trekk ut meiningsberande ord frå tekst."""
    ord_lista = re.findall(r"\b\w{4,}\b", txt.lower())
    return {w for w in ord_lista if w not in STOPORD}

def finn_semantiske_koplingar(alle_notat):
    """
    For kvart notat: finn andre notat med høgt nøkkelord-overlapp
    som IKKJE allereie er lenkja.
    Returnerer: { filepath: [relaterte_stiar] }
    """
    # Bygg nøkkelord-sett per notat
    nøkkelord_per_fil = {
        path: nøkkelord(txt)
        for path, txt in alle_notat.items()
    }

    koplingar = defaultdict(list)

    for path, ord_sett in nøkkelord_per_fil.items():
        eksisterande = finn_eksisterande_lenker(alle_notat[path])

        for annan_path, andre_ord in nøkkelord_per_fil.items():
            if annan_path == path: continue
            if annan_path.stem.lower() in eksisterande: continue

            overlapp = len(ord_sett & andre_ord)
            if overlapp >= MIN_OVERLAP:
                koplingar[path].append((overlapp, annan_path))

        # Sorter etter overlapp, ta topp 3
        koplingar[path].sort(reverse=True)
        koplingar[path] = [p for _, p in koplingar[path][:3]]

    return koplingar

def legg_til_relaterte(txt, relaterte_stiar):
    """Legg til / oppdater 'Relaterte notat'-linje nedst i notatet."""
    lenker   = " · ".join(f"[[{p.stem}]]" for p in relaterte_stiar)
    ny_linje = f"\n---\n*Relaterte notat: {lenker}*"

    # Fjern gammal linje viss ho finst
    txt = re.sub(r"\n---\n\*Relaterte notat:.*?\*", "", txt)
    return txt.rstrip() + ny_linje

# ── Hovudprogram ───────────────────────────────────────────────────────────────
print(f"Vault: {VAULT.name}")
print("Les alle notat...", end=" ", flush=True)
alle_notat = les_vault()
alle_namn  = [path.stem for path in alle_notat]
print(f"{len(alle_notat)} notat funne.\n")

# Del 1 — Eksplisitt lenking
print("── Del 1: Eksplisitt lenking ──────────────────────────")
link_endringar = 0
link_filer     = 0

for path, txt in alle_notat.items():
    ny_txt, endringar = legg_til_wikilenker(path, txt, alle_namn)
    if endringar:
        print(f"  {path.stem}: +{len(endringar)} lenker → {', '.join(endringar)}")
        link_endringar += len(endringar)
        link_filer     += 1
        if not DRY_RUN:
            path.write_text(ny_txt, encoding="utf-8")
            alle_notat[path] = ny_txt  # Oppdater for semantisk analyse

if link_filer == 0:
    print("  Ingen manglande lenker funne — vaulten er allereie godt lenka!")
print(f"\n  Totalt: {link_endringar} lenker i {link_filer} filer.\n")

# Del 2 — Semantiske koplingar
print("── Del 2: Semantiske koplingar ────────────────────────")
sem_koplingar = finn_semantiske_koplingar(alle_notat)
sem_filer     = 0

for path, relaterte in sem_koplingar.items():
    if not relaterte: continue
    namn_lista = ", ".join(f"[[{p.stem}]]" for p in relaterte)
    print(f"  {path.stem} ↔ {namn_lista}")
    sem_filer += 1
    if not DRY_RUN:
        ny_txt = legg_til_relaterte(alle_notat[path], relaterte)
        path.write_text(ny_txt, encoding="utf-8")

if sem_filer == 0:
    print("  Ingen nye semantiske koplingar funne.")
print(f"\n  Totalt: {sem_filer} notat med nye koplingar.\n")

# Oppsummering
print("══════════════════════════════════════════════════════")
if DRY_RUN:
    print(f"FØREHANDSVISNING ferdig.")
    print(f"  → {link_endringar} wikilenker ville bli lagt til")
    print(f"  → {sem_filer} 'Relaterte notat'-seksjonar ville bli lagt til")
    print(f"\nKøyr med --skriv for å lagre endringar:")
    print(f"  python stc_autolink.py --skriv")
else:
    print(f"FERDIG!")
    print(f"  → {link_endringar} wikilenker lagt til")
    print(f"  → {sem_filer} 'Relaterte notat'-seksjonar lagt til")
    print(f"\nOpne Obsidian-grafen for å sjå koplingsnettet!")
