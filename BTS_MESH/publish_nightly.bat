@echo off
rem ============================================================================
rem  publish_nightly.bat - the LOGGING WRAPPER for the nightly R2 publish.
rem  Cowork, 2026-07-30.  DURABLE TOOL - lives in the tree, not on the Desktop.
rem
rem  WHY IT EXISTS (PLM-02 / PLM-03, both measured 2026-07-30):
rem    "R2 Publish Nightly" runs D:\R2Cloner\Publish-to-R2_KEYED.bat directly.
rem    That bat writes NO log. The task fired at 22:00:01 with Last Result 0 and
rem    nothing on disk changed - so a failing publish would have been invisible.
rem    Meanwhile "BTS Publish Watch" has run EVERY MINUTE since 2026-07-14 and
rem    written ONE line, because it watches for an event the raw bat never emits.
rem
rem  THE SCAR IT OBEYS: a bat opens its log FIRST and tees to it. "pause" is not
rem  a report, and a window that closes takes the only evidence with it.
rem
rem  SECURITY: the KEYED bat holds the R2 secret in plaintext. This wrapper CALLS
rem  it and captures its STDOUT. It never reads, prints, copies or logs the file.
rem ============================================================================
rem  ---------------------------------------------------------------------------
rem  🔴 2026-08-12: A JOB CANNOT PUBLISH ITS OWN LIVE LOG. Fixed in TWO steps,
rem  because the first fix was based on an assumption I did not check.
rem
rem  OUT was PhD2_DATA_ARCHIVE\00_WORKING\R2_PUBLISH_LAST.log - inside the subtree
rem  rclone publishes. Every run wrote that file WHILE rclone hashed and uploaded
rem  it, so rclone correctly reported "corrupted on transfer: md5 hashes differ"
rem  and, on 2026-08-12, "exceeded maximum number of attempts". That one
rem  self-inflicted error is what the nightly publish has been reporting.
rem
rem  FIRST FIX, AND IT FAILED: moved to BTS_MESH, on the stated reasoning that
rem  "BTS_MESH is outside the published subtree, which is why the TALLY has never
rem  had this problem." THAT WAS AN ASSUMPTION, WRITTEN AS A FACT, AND IT WAS
rem  WRONG - the very next run failed with src(...\Ai\BTS_MESH). The publish
rem  covers BTS_MESH too.
rem
rem  AND THE TALLY'S IMMUNITY HAD A DIFFERENT CAUSE ENTIRELY: PUBLISH.log is
rem  appended BEFORE and AFTER the rclone run, never DURING it, so it is stable
rem  while rclone reads it. Same folder, opposite behaviour - the folder was never
rem  the variable. I reasoned from the wrong difference.
rem
rem  SECOND FIX: V:\Ai\_queue\ - a different tree, not published by anything.
rem  ==> THE RULE: the log must be written OUTSIDE EVERY PUBLISHED ROOT, and
rem      "which roots are published" is a thing to CHECK, not to remember.
rem  ---------------------------------------------------------------------------
setlocal
set TARGET=D:\R2Cloner\Publish-to-R2_KEYED.bat
set OUT=V:\Ai\_queue\R2_PUBLISH_LAST.log
set TALLY=V:\Research4\Ai\BTS_MESH\PUBLISH.log

> "%OUT%" echo ==== R2 nightly publish  %DATE% %TIME% ====
>> "%OUT%" echo script: %TARGET%
>> "%OUT%" echo.

if not exist "%TARGET%" (
  >> "%OUT%" echo [FATAL] publisher not found: %TARGET%
  >> "%TALLY%" echo [%DATE% %TIME%] FAIL  publish exit=9009  reason=publisher missing
  exit /b 9009
)

call "%TARGET%" >> "%OUT%" 2>&1
set RC=%ERRORLEVEL%

>> "%OUT%" echo.
>> "%OUT%" echo ==== exit=%RC%  %DATE% %TIME% ====
if "%RC%"=="0" (
  >> "%TALLY%" echo [%DATE% %TIME%] OK    publish exit=0  log=%OUT%
) else (
  >> "%TALLY%" echo [%DATE% %TIME%] FAIL  publish exit=%RC%  log=%OUT%
)
exit /b %RC%
