@echo off
REM ============================================================================
REM ASK_SnG.bat  --  ask SGH and GEM the same design brief, independently,
REM                  and settle whether the Google keys are actually dead.
REM Created 2026-07-26 by Cowork.
REM
REM WHY NATIVE AND NOT THE SANDBOX (two measured reasons):
REM   1. Cowork's shell is killed at 45 s. Both nodes need minutes.
REM   2. From the sandbox EVERY googleapis host returns an HTML 403
REM      (server-timing: gfet4t7) -- including keyless discovery. That is an
REM      egress block on the sandbox IP, NOT a credential fault. This bat
REM      re-runs the probes where the bytes are real. Windows is ground truth.
REM
REM Writes into ...\PhD2_DATA_ARCHIVE\00_WORKING\ :
REM   RAILCHECK_WINDOWS_2026-07-26.txt   <- read this first
REM   SnG_REPLY_SGH_2026-07-26.md
REM   SnG_REPLY_GEM_2026-07-26.md
REM   SnG_COMPARE_2026-07-26.md
REM ============================================================================
setlocal
set PYTHONIOENCODING=utf-8
set MESH=V:\Research4\Ai\BTS_MESH
set LOG=%MESH%\sng_ask.log

cd /d "%MESH%"
where py >nul 2>&1 && (set PY=py -3) || (set PY=python)

echo. >> "%LOG%"
echo ================================================== >> "%LOG%"
echo [%DATE% %TIME%] ASK_SnG start >> "%LOG%"

echo.
echo   Asking SGH and GEM the same brief, independently.
echo   This takes a few minutes. Leave this window open.
echo.

REM ONE invocation only. An earlier draft of this file ran it twice (once to the
REM console, once to the log) which would have double-charged the SGH rail.
%PY% "%MESH%\sng_ask.py"
set RC=%ERRORLEVEL%
echo [%DATE% %TIME%] ASK_SnG exit=%RC% >> "%LOG%"
echo.
echo   Done. Replies are in:
echo     V:\Research4\Ai\PhD2_DATA_ARCHIVE\00_WORKING\
echo.
pause
endlocal
