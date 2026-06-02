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

## Oppsett

### Krav
```
pip install anthropic transformers accelerate torch
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

## Modell
- **Claude:** `claude-haiku-4-5` (rask, billeg, god nok for notat)
- **Whisper:** `NbAiLab/nb-whisper-medium` (norsk-optimalisert, ~1.5 GB)

## Vault-struktur
```
Obsidian-vault/
├── AI/Lyd/Lyd_inn/     ← dropp lydfiler her
├── AI/Lyd/Lyd_arkiv/   ← arkiverte lydfiler
└── Studie/Medisin/...  ← notat havnar her
```

---
*Del av Project Ciel — personleg Obsidian-assistent for Katchi*
