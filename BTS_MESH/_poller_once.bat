@echo off
REM Silent single host poll, used by the "BTS PolleR" Windows Scheduled Task (hourly).
REM Appends to PolleR.log. Reader only -- no browser, no dispatch, no spend.
cd /d "V:\Research4\Ai\BTS_MESH"
echo [%date% %time%] PolleR --once >> PolleR.log
python bts_poller.py --once >> PolleR.log 2>&1
