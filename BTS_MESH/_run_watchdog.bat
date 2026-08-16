@echo off
REM ── BTS WATCHDOG — the 10-minute pulse ───────────────────────────────────────────────────────
REM Keith, 2026-07-13: "Start watchdog, set for 10 minute checks and que all open tasks ...
REM distribute across MESH (all but copilot)."
REM
REM Free rails only. The PAID SGH API stays OFF: an unattended loop with a credit card is how you
REM wake up to a surprise bill, and one grounded search on that rail costs ~$1.30 against a $10/mo
REM budget. To allow it: set ALLOW_PAID=1 and pass --paid-cap 0.50
REM
REM Leave this window OPEN. Ctrl-C stops it. Log: BTS_MESH\WATCHDOG.log
REM ─────────────────────────────────────────────────────────────────────────────────────────────
title BTS WATCHDOG - 10 min pulse
cd /d "%~dp0"
echo.
echo   BTS WATCHDOG  -  10 minute checks  -  free rails only  -  COPILOT excluded
echo   queue: QUEUE.json    log: WATCHDOG.log    stop: Ctrl-C
echo.
python bts_watchdog.py --interval 10
echo.
echo   watchdog exited.
pause
