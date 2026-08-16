@echo off
REM Launch Jack's Mesh Command over http://localhost so YouTube embeds work
REM (opening the .html directly as a file:// page causes YouTube "error 153").
cd /d "%~dp0"
REM refresh the live mesh snapshot the dashboard reads (registry / signals / counters)
python bts_state.py . 2>nul
start "" "http://localhost:8765/jack_command.html"
echo Serving this folder at http://localhost:8765  (close this window to stop)
echo Dashboard shows LIVE mesh data from mesh_state.json (run: python bts.py doctor . to health-check)
python -m http.server 8765
