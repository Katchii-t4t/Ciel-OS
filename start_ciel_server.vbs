' start_ciel_server.vbs — Startar Ciel-hjernen (FastAPI) heilt usynleg
' Legg i shell:startup for automatisk start ved innlogging.
'
' Robust: les ANTHROPIC_API_KEY direkte frå den LAGRA User-miljøvariabelen
' (ikkje frå det kallande skalet), og gir han vidare til server-prosessen via
' PROCESS-scope så pythonw arvar han. API-nøkkelen vert ALDRI hardkoda her.

Dim sh
Set sh = CreateObject("WScript.Shell")

' Les nøkkelen direkte frå den persistente User-variabelen (uavhengig av skal)
Dim apiKey
apiKey = sh.Environment("USER").Item("ANTHROPIC_API_KEY")

' Gi miljøet vidare til child-prosessen (PROCESS-scope = berre dette treet)
If apiKey <> "" Then
    sh.Environment("PROCESS").Item("ANTHROPIC_API_KEY") = apiKey
End If
sh.Environment("PROCESS").Item("KMP_DUPLICATE_LIB_OK") = "TRUE"
sh.Environment("PROCESS").Item("PYTHONIOENCODING") = "utf-8"

' Finn Python. MERK: bruk python.exe (IKKJE pythonw.exe) — pythonw gjev
' sys.stdout = None, og agent-koden gjer sys.stdout.reconfigure()/print() ved
' oppstart → krasjar lydlaust. python.exe med skjult vindauge (Run-stil 0)
' har ekte stdout og køyrer usynleg.
Dim fso, py
Set fso = CreateObject("Scripting.FileSystemObject")
py = "C:\Users\Karthik\anaconda3\python.exe"
If Not fso.FileExists(py) Then py = "python.exe"

Dim base
base = "C:\Users\Karthik\ciel\"
sh.CurrentDirectory = base

' 0 = heilt usynleg, False = ikkje vent
sh.Run Chr(34) & py & Chr(34) & " """ & base & "ciel_server.py""", 0, False

Set sh = Nothing
