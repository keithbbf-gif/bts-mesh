@echo off
REM ============================================================================
REM  Recreate the Desktop launcher if it goes missing again.
REM  It vanished once (2026-07-13) — OneDrive-redirected Desktops do that.
REM  Run this and the front door is back. The launcher itself is only a shim;
REM  all the real logic lives in BTS_MESH, so this is safe to run any time.
REM ============================================================================
copy /Y "V:\Research4\Ai\BTS_MESH\_desktop_launcher_master.vbs" "%USERPROFILE%\OneDrive\Desktop\Jack's Mesh Command.vbs" >nul 2>&1
if errorlevel 1 (
  echo Could not write to the OneDrive Desktop. Trying the plain Desktop...
  copy /Y "V:\Research4\Ai\BTS_MESH\_desktop_launcher_master.vbs" "%USERPROFILE%\Desktop\Jack's Mesh Command.vbs" >nul 2>&1
)
echo Desktop launcher restored.
pause
