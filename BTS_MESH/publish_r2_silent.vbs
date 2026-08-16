' ============================================================================
'  PUBLISH to R2 (silent).vbs   -   double-click. Nothing appears. It just goes.
'
'  WHY THIS EXISTS (Keith, 2026-07-29): "can you not somehow have it execute in
'  the background, instead of on my screen?"  Rule 2 - the desktop is not a
'  runtime. Every publish so far has been launched with `cmd /k` through the Run
'  dialog, which parks a console in front of whatever he was doing.
'
'  IT ALSO REMOVES A REAL FAILURE MODE, not just an annoyance. A visible console
'  can be put into QuickEdit selection mode by ONE stray click, and Windows then
'  SUSPENDS the process - silently, with no log line, looking exactly like a
'  hang. That cost a session on 2026-07-28 (upsjudge, title bar read "Select
'  C:\Windows\system32\cmd.exe"). A hidden console cannot be clicked into.
'
'  Window style 0 = hidden. False = do not wait, so the double-click returns
'  immediately and the transfer carries on by itself.
'
'  VERIFY IT LATER, DO NOT ASSUME IT:
'    log      V:\Research4\00_WORKING\R2_PUBLISH_LAST.log   (overwritten each run)
'    cloud    fetch a file written THIS session from ai.dchambers.com and read
'             the BYTES - HTTP 200 alone is not proof the content updated.
'
'  The keys live inside the bat, in D:\R2Cloner, deliberately OUTSIDE the
'  published tree. This wrapper never reads, prints or copies them.
' ============================================================================
Option Explicit

Dim sh, fso, bat, log, cmd
Set sh  = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

bat = "D:\R2Cloner\Publish-to-R2_KEYED.bat"
log = "V:\Research4\00_WORKING\R2_PUBLISH_LAST.log"

If Not fso.FileExists(bat) Then
    MsgBox "Publish bat not found:" & vbCrLf & bat & vbCrLf & vbCrLf & _
           "D:\R2Cloner is the ONLY route to the ITC mirror. If the drive is " & _
           "not mounted, nothing can publish.", 16, "R2 publish"
    WScript.Quit 1
End If

If Not fso.FolderExists("V:\Research4\00_WORKING") Then
    fso.CreateFolder("V:\Research4\00_WORKING")
End If

' cmd /c so the shell closes itself when rclone finishes.
cmd = "cmd /c """"" & bat & """ > """ & log & """ 2>&1"""
sh.Run cmd, 0, False

' One quiet confirmation that it STARTED - not that it finished. Saying
' "published" here would be a launcher claiming success on behalf of a process
' it never waited for, which is exactly how FANOUT_UI.bat printed "Both
' launched" while neither node had run.
sh.Popup "R2 publish started in the background." & vbCrLf & vbCrLf & _
         "Log: " & log & vbCrLf & _
         "This says STARTED, not finished - check the log, or fetch a file " & _
         "from ai.dchambers.com to confirm the bytes actually changed.", _
         6, "R2 publish", 64
