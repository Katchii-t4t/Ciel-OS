' start_ciel.vbs — Startar alle Ciel-vault-agentar heilt usynleg
' (stc_agent = Ciel: i Obsidian, stc_pdf = PDF-import, stc_lyd = lydtranskripsjon)
' Legg i shell:startup for automatisk start ved innlogging.
'
' MERK: bruk python.exe (IKKJE pythonw.exe) med skjult vindauge (Run-stil 0).
' pythonw gjev sys.stdout = None, og agentane gjer sys.stdout.reconfigure()/print()
' ved oppstart → krasjar lydlaust. python.exe har ekte stdout og køyrer usynleg.

Dim sh
Set sh = CreateObject("WScript.Shell")

' Les API-nøkkelen direkte frå den lagra User-variabelen og gi vidare til child
Dim apiKey
apiKey = sh.Environment("USER").Item("ANTHROPIC_API_KEY")
If apiKey <> "" Then
    sh.Environment("PROCESS").Item("ANTHROPIC_API_KEY") = apiKey
End If
sh.Environment("PROCESS").Item("KMP_DUPLICATE_LIB_OK") = "TRUE"
sh.Environment("PROCESS").Item("PYTHONIOENCODING") = "utf-8"

Dim fso, py
Set fso = CreateObject("Scripting.FileSystemObject")
py = "C:\Users\Karthik\anaconda3\python.exe"
If Not fso.FileExists(py) Then py = "python.exe"

Dim base
base = "C:\Users\Karthik\.claude\"

' 0 = heilt usynleg, False = ikkje vent (start alle parallelt)
sh.Run Chr(34) & py & Chr(34) & " """ & base & "stc_agent.py""", 0, False
sh.Run Chr(34) & py & Chr(34) & " """ & base & "stc_pdf.py""",   0, False
sh.Run Chr(34) & py & Chr(34) & " """ & base & "stc_lyd.py""",   0, False
sh.Run Chr(34) & py & Chr(34) & " """ & base & "stc_pdf_embed.py""", 0, False

Set sh = Nothing
