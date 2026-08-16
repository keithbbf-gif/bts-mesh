' ============================================================================
'  Jack's Mesh Command — ONE CLICK. That is the whole spec.
'
'  Keith, 2026-07-12:
'    "The Dash should never require more than one click to fully load/execute,
'     even if it requires a bat that runs the python or whatever.
'     I prefer elegant to not."
'
'  So: double-click this file and you get a fully-loaded dashboard. Nothing else.
'  No console windows, no second window to babysit, no "now press TEST".
'
'  WHAT IT DOES, in order, and why the order matters:
'    1. Runs bts_snapshot.py and WAITS for it. This writes dash.json (disk caps,
'       burn, policy) and mesh_state.json (the signal log). We WAIT because the
'       page reads those files on load — open the browser first and it would show
'       the previous run's numbers.
'    2. Starts bts_serve.py with pythonw.exe — the windowless Python host. No
'       console to hide, nothing to accidentally close and kill the server.
'       If a server is already listening on 8765, bts_serve exits cleanly and we
'       reuse it, so clicking this twice is harmless.
'    3. Opens the dashboard on http://localhost:8765 — NOT file://. A file:// page
'       cannot fetch dash.json (browsers block local XHR) and every panel would
'       silently fall back to hardcoded values. That was the bug.
'
'  To STOP the server: Task Manager -> end pythonw.exe. (Or just leave it; it is
'  a localhost-only static server that costs nothing when idle.)
'
'  Debug variant: run_dash.bat does the same thing with a visible console, for
'  when something breaks and you want to see why.
' ============================================================================
Option Explicit

Dim sh, fso, here, py, pyw, cmd
Set sh  = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

here = Left(WScript.ScriptFullName, InStrRev(WScript.ScriptFullName, "\"))
sh.CurrentDirectory = here

' --- find Python. "python" is usual; "py" is the launcher shipped with python.org installs. ---
py  = "python"
pyw = "pythonw"
If Not HasCmd("python") Then
    If HasCmd("py") Then
        py  = "py"
        pyw = "py -w"          ' the launcher's windowless mode
    End If
End If

' --- 1. refresh the snapshot, and WAIT for it (0 = hidden, True = wait) -------------------
'     dash.json must exist and be current BEFORE the browser reads it.
sh.Run "cmd /c " & py & " bts_snapshot.py", 0, True

' --- 2. start the server windowless. pythonw = no console at all. -------------------------
'     bts_serve is idempotent: if 8765 is already served, it exits quietly and we reuse it.
sh.Run pyw & " bts_serve.py", 0, False

' --- 3. give the socket a moment to bind, then open the page ------------------------------
WScript.Sleep 1200
sh.Run "http://localhost:8765/jack_command.html", 1, False


' -----------------------------------------------------------------------------------------
Function HasCmd(name)
    Dim rc
    On Error Resume Next
    rc = sh.Run("cmd /c where " & name & " >nul 2>&1", 0, True)
    HasCmd = (Err.Number = 0 And rc = 0)
    On Error GoTo 0
End Function
