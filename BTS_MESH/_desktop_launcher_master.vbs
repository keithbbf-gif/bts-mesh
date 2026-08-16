' ============================================================================
'  JACK'S MESH COMMAND — MASTER COPY of the desktop launcher.
'  This is the source of truth. _RECREATE_DESKTOP_LAUNCHER.bat copies it to the
'  Desktop. If the Desktop shortcut disappears again (it did, 2026-07-13 — an
'  OneDrive-redirected Desktop will do that), run that bat and the front door is back.
'  Keep the LOGIC here, not on the Desktop.
' ============================================================================
Option Explicit

Dim sh, fso, home, py, pyw
Set sh  = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

home = "V:\Research4\Ai\BTS_MESH"

If Not fso.FolderExists(home) Then
    MsgBox "BTS_MESH not found at:" & vbCrLf & home, 16, "Jack's Mesh Command"
    WScript.Quit 1
End If
sh.CurrentDirectory = home

py  = "python"
pyw = "pythonw"
If Not HasCmd("python") Then
    If HasCmd("py") Then
        py  = "py"
        pyw = "py -w"
    Else
        MsgBox "Python is not on PATH.", 16, "Jack's Mesh Command"
        WScript.Quit 1
    End If
End If

' 0. kill a stale server first — a plain http.server on 8765 serves the page with NO /api
'    routes, and every panel then silently shows hardcoded values. Worse than nothing.
sh.Run "cmd /c taskkill /F /IM pythonw.exe >nul 2>&1", 0, True

' 1. refresh dash.json (surfaces, burn, policy, measured DRIVE SPEEDS) — and WAIT for it
sh.Run "cmd /c " & py & " bts_snapshot.py", 0, True

' 2. windowless server (owns /api/bench, /api/burn, /api/surfaces, /api/policy)
sh.Run pyw & " bts_serve.py", 0, False

' 3. bind, then open — http://, NEVER file:// (file:// cannot fetch dash.json)
WScript.Sleep 1400
sh.Run "http://localhost:8765/jack_command.html", 1, False


Function HasCmd(name)
    Dim rc
    On Error Resume Next
    rc = sh.Run("cmd /c where " & name & " >nul 2>&1", 0, True)
    HasCmd = (Err.Number = 0 And rc = 0)
    On Error GoTo 0
End Function
