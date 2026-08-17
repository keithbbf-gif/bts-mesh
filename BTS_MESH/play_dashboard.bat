@echo off
REM Launch Jack's Mesh Command over http://localhost so YouTube embeds work
REM (opening the .html directly as a file:// page causes YouTube "error 153").
REM
REM ⚠ MUST be bts_serve.py — `python -m http.server 8765` has NO /api routes.
REM That is the S-10 class: a foreign server on 8765 looks identical to a working
REM dashboard and silently kills /api/burn, /api/bench, and the cockpit paint.
cd /d "%~dp0"
start "" "http://localhost:8765/jack_command.html"
echo Serving via bts_serve.py at http://localhost:8765
echo   /api/burn  live GEM + SGH + packets + KMesh cockpit
echo   /api/bench real mesh ^<TEST^>
echo Close this window to stop.
python bts_serve.py
