@echo off
:: StC-agent — startar automatisk ved innlogging
:: Legg dette i Windows Startup-mappa (sjå instruksjonar nedst)

:: ── API-nøkkel er sett som Windows-miljovariabel (ikkje hardkoda her) ──

:: ── Start agenten i bakgrunnen ───────────────────────────
start "StC-agent" /min python "C:\Users\Karthik\.claude\stc_agent.py"

:: ── For å leggje dette i Windows Startup: ───────────────
:: 1. Trykk Win+R
:: 2. Skriv: shell:startup
:: 3. Kopier denne .bat-fila inn i den mappa
:: 4. Ferdig — agenten startar automatisk ved kvar innlogging
