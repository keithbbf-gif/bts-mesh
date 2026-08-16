' ============================================================================
'  bts_publish_watch.vbs  --  SILENT, NO-WINDOW ITC (Cloudflare R2) PUBLISH WATCHER
'  Created 2026-07-14 for Keith. Mirrors the PolleR hidden-task pattern.
'
'  WHAT IT IS: a flag-driven, hidden watcher. A Windows Scheduled Task
'  ("BTS Publish Watch") runs this every 1 minute. Each run does NOTHING
'  unless a flag file is present -- then it publishes the ITC surface to
'  Cloudflare R2 (ai.dchambers.com) in the BACKGROUND, with NO console
'  window, so it never interrupts Keith's desktop. GDX/ODX are instant
'  local writes; ITC now becomes a batched, no-interruption background push.
'
'  WHAT IT IS NOT: it NEVER dispatches a node, NEVER calls a model, NEVER
'  spends a cent on inference. It only runs the R2 publish bat, and only when
'  the flag is set. No flag -> silent exit (the common case, every minute).
'
'  *** SECURITY -- NON-NEGOTIABLE ***
'  D:\R2Cloner\Publish-to-R2_KEYED.bat holds the R2 API keys in PLAINTEXT.
'  This script INVOKES it BY PATH ONLY. It NEVER opens, reads, prints, echoes,
'  or copies that bat or anything in D:\R2Cloner, and it does NOT capture the
'  bat's stdout (which could echo a key line). It records ONLY the process
'  exit code + a timestamp + OK/FAIL to PUBLISH.log. No secret can reach the
'  log, a STATE event, or any file this script writes.
'
'  TRIGGER (Cowork or a human): stage files into the published subtree
'  V:\Research4\Ai\PhD2_DATA_ARCHIVE, then create the flag file:
'      V:\Research4\Ai\BTS_MESH\PUBLISH.flag        (empty, or a one-line reason)
'  Within ~1 min this task publishes with no window, renames the flag to
'  PUBLISH.done.<timestamp> (so it does not re-fire), and emits ONE ITC
'  'publish' STATE event.
'
'  FAILURE POLICY: on a failed publish the flag is LEFT in place (so it retries
'  next tick), a FAIL line is logged, and a publish_fail STATE event is emitted.
'  After 3 CONSECUTIVE fails the flag is renamed PUBLISH.stuck and a
'  publish_stuck event is emitted, so it stops hammering. To reset: delete or
'  rename PUBLISH.stuck and drop a fresh PUBLISH.flag.
'
'  OVERLAP GUARD: a publish can take longer than the 1-min tick. A run-lock
'  (PUBLISH.running) prevents a second tick from starting a second rclone run.
'
'  STDIN is redirected from NUL when the bat runs, so any trailing `pause` /
'  `set /p` in the bat returns immediately instead of hanging this hidden run.
' ============================================================================
Option Explicit

Dim sh, fso
Set sh  = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

Dim home, flag, logf, bat, r2dir, failCountFile, runLock, pyexe
home          = "V:\Research4\Ai\BTS_MESH"
flag          = home & "\PUBLISH.flag"
logf          = home & "\PUBLISH.log"
r2dir         = "D:\R2Cloner"
bat           = r2dir & "\Publish-to-R2_KEYED.bat"    ' invoked by path ONLY -- never read
failCountFile = home & "\PUBLISH.failcount"
runLock       = home & "\PUBLISH.running"

' --- 0. NO FLAG -> do absolutely nothing (this is what happens ~every minute) --
If Not fso.FileExists(flag) Then
    WScript.Quit 0
End If

sh.CurrentDirectory = home

' --- 0b. a publish already in progress? do not start a second rclone run -------
If fso.FileExists(runLock) Then
    Dim lockAgeMin
    On Error Resume Next
    lockAgeMin = DateDiff("n", fso.GetFile(runLock).DateLastModified, Now)
    On Error GoTo 0
    If lockAgeMin < 15 Then
        WScript.Quit 0            ' fresh lock -> a publish is running; stand down silently
    End If
    On Error Resume Next          ' stale lock (>15 min): a prior run died; steal it
    fso.DeleteFile runLock, True
    On Error GoTo 0
End If

' --- 0c. sanity: the publish bat must exist (we check the PATH, never the body) -
If Not fso.FileExists(bat) Then
    LogLine "FAIL  publish bat not found at path (path checked, contents never read)"
    WScript.Quit 1
End If

' --- 1. read the flag's optional one-line reason (NOT a secret; Cowork wrote it)-
Dim reason
reason = ReadFirstLine(flag)
If reason = "" Then reason = "publish"

' --- 2. resolve python for the STATE emit (mirror JDash: python -> py fallback) --
pyexe = "python"
If Not HasCmd("python") Then
    If HasCmd("py") Then pyexe = "py" Else pyexe = ""
End If

' --- 3. take the run-lock, publish HIDDEN, capture ONLY the exit code ----------
TouchFile runLock

Dim cmd, rc
' cd into R2Cloner (matches how the bat is run today) then invoke it BY PATH.
' window style 0 = hidden; True = wait and return the bat's exit code.
' We deliberately do NOT redirect/capture stdout -- the bat may echo a key line,
' so raw stdout is never touched. `< nul` feeds EOF so a trailing pause won't hang.
cmd = "cmd /c cd /d " & Chr(34) & r2dir & Chr(34) & " && " & _
      Chr(34) & bat & Chr(34) & " < nul"
rc = sh.Run(cmd, 0, True)

On Error Resume Next
fso.DeleteFile runLock, True
On Error GoTo 0

' --- 4. branch on the exit code -----------------------------------------------
If rc = 0 Then
    ' SUCCESS: rename the flag so it cannot re-fire, log OK, emit ONE STATE event
    On Error Resume Next
    fso.MoveFile flag, home & "\PUBLISH.done." & TimeStamp()
    On Error GoTo 0
    ResetFailCount
    LogLine "OK    publish exit=0  reason=" & reason
    EmitState "COWORK ITC publish " & Chr(34) & Sanitize(reason & " / ok") & Chr(34) & " out"
    WScript.Quit 0
Else
    ' FAILURE: leave the flag in place to retry; bump the consecutive-fail counter
    Dim fails
    fails = BumpFailCount()
    LogLine "FAIL  publish exit=" & rc & "  reason=" & reason & "  consecutive_fails=" & fails
    If fails >= 3 Then
        On Error Resume Next
        fso.MoveFile flag, home & "\PUBLISH.stuck"
        On Error GoTo 0
        ResetFailCount
        EmitState "COWORK ITC publish_stuck " & Chr(34) & "3 fails, stopped (exit=" & rc & ")" & Chr(34) & " out"
    Else
        EmitState "COWORK ITC publish_fail " & Chr(34) & "exit=" & rc & " (retrying)" & Chr(34) & " out"
    End If
    WScript.Quit rc
End If


' -------------------------------------------------------------------- helpers --
Sub LogLine(msg)
    On Error Resume Next
    Dim f
    Set f = fso.OpenTextFile(logf, 8, True)      ' 8=ForAppending, True=create if absent
    f.WriteLine "[" & Now & "] " & msg
    f.Close
    On Error GoTo 0
End Sub

Function ReadFirstLine(path)
    ReadFirstLine = ""
    On Error Resume Next
    Dim f, line
    Set f = fso.OpenTextFile(path, 1, False)     ' 1=ForReading
    If Not f.AtEndOfStream Then line = f.ReadLine
    f.Close
    ReadFirstLine = Trim(line)
    On Error GoTo 0
End Function

Sub TouchFile(path)
    On Error Resume Next
    Dim f
    Set f = fso.OpenTextFile(path, 2, True)       ' 2=ForWriting (truncate/create)
    f.WriteLine Now
    f.Close
    On Error GoTo 0
End Sub

Sub TouchWith(path, text)
    On Error Resume Next
    Dim f
    Set f = fso.OpenTextFile(path, 2, True)
    f.Write text
    f.Close
    On Error GoTo 0
End Sub

Function TimeStamp()
    Dim d
    d = Now
    TimeStamp = Year(d) & Pad(Month(d)) & Pad(Day(d)) & "_" & _
                Pad(Hour(d)) & Pad(Minute(d)) & Pad(Second(d))
End Function

Function Pad(n)
    If n < 10 Then Pad = "0" & n Else Pad = CStr(n)
End Function

Function BumpFailCount()
    Dim n
    n = 0
    On Error Resume Next
    If fso.FileExists(failCountFile) Then n = CInt(ReadFirstLine(failCountFile))
    On Error GoTo 0
    n = n + 1
    TouchWith failCountFile, CStr(n)
    BumpFailCount = n
End Function

Sub ResetFailCount()
    On Error Resume Next
    If fso.FileExists(failCountFile) Then fso.DeleteFile failCountFile, True
    On Error GoTo 0
End Sub

Function Sanitize(s)
    ' keep the STATE detail a single plain token: no quotes/newlines that could
    ' break the argument. (There is no secret here to strip -- just hygiene.)
    Dim t
    t = Replace(s, Chr(34), "'")
    t = Replace(t, vbCr, " ")
    t = Replace(t, vbLf, " ")
    Sanitize = t
End Function

Sub EmitState(argline)
    ' fire ONE bts_state event (carries NO secret -- just "publish"/"fail" + reason).
    ' Hidden (0), non-blocking (False). If python is unavailable, log and skip.
    On Error Resume Next
    If pyexe = "" Then
        LogLine "WARN  python not on PATH -> STATE emit skipped: " & argline
        Exit Sub
    End If
    sh.Run pyexe & " bts_state.py --emit " & argline, 0, False
    On Error GoTo 0
End Sub

Function HasCmd(name)
    Dim rc2
    On Error Resume Next
    rc2 = sh.Run("cmd /c where " & name & " >nul 2>&1", 0, True)
    HasCmd = (Err.Number = 0 And rc2 = 0)
    On Error GoTo 0
End Function
