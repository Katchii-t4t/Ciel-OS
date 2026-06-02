' start_ciel.vbs — Startar alle Ciel-agentar heilt usynleg
' Ingen vindauge, ingen ikon i oppgåvelinja
' Legg i shell:startup for automatisk start ved innlogging

Dim sh
Set sh = CreateObject("WScript.Shell")

' Les API-nøkkel frå Windows brukar-miljøvariablar
Dim apiKey
apiKey = sh.ExpandEnvironmentStrings("%ANTHROPIC_API_KEY%")

' Sett miljøvariablar for denne sesjonen
sh.Environment("USER").Item("ANTHROPIC_API_KEY") = apiKey
sh.Environment("USER").Item("KMP_DUPLICATE_LIB_OK") = "TRUE"
sh.Environment("USER").Item("PYTHONIOENCODING") = "utf-8"

Dim py
py = "C:\Users\Karthik\anaconda3\pythonw.exe"

Dim base
base = "C:\Users\Karthik\.claude\"

' 0 = heilt usynleg, False = ikkje vent (start alle parallelt)
sh.Run Chr(34) & py & Chr(34) & " """ & base & "stc_agent.py""", 0, False
sh.Run Chr(34) & py & Chr(34) & " """ & base & "stc_pdf.py""",   0, False
sh.Run Chr(34) & py & Chr(34) & " """ & base & "stc_lyd.py""",   0, False

Set sh = Nothing
