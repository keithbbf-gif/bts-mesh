@echo off
REM ============================================================================
REM run_dash.bat — the ONE way to start Jack's Mesh Command.
REM
REM Keith, 2026-07-12:
REM   "the disk cap can be static updated only at the Open or Close of the Dash"
REM   "make it run the python when I click Test - use a Bat file if you need to"
REM
REM So the order here is deliberate:
REM   1. Refresh the SNAPSHOT (dash.json) BEFORE the page opens. This is the slow
REM      part — it walks OneDrive (~105 GB of files) to size it. Far too slow to
REM      poll; exactly right to do once, at Open.
REM   2. Start bts_serve.py, which serves the page AND gives <TEST> a way to
REM      actually execute Python (a browser cannot run a script by itself — the
REM      button has to call the server).
REM   3. Open the dashboard on http://, NOT file://.  A file:// page cannot fetch
REM      dash.json (browsers block it) and every panel would fall back to its
REM      hardcoded value and say "unknown" — which is the bug Keith just hit.
REM ============================================================================
cd /d "%~dp0"

REM bts_snapshot.py now ALSO regenerates mesh_state.json (the signal log's source).
REM The old .vbs ran `python bts_state.py .` separately; that step got dropped when the launcher
REM changed, which is why the SIGNAL LOG went stale. It lives inside bts_snapshot.py now, so it
REM can never be forgotten again — Open and <TEST> both refresh it.
REM [0/3] KILL ANY STALE SERVER. The old launcher ran `python -m http.server 8765`; if that is
REM still alive, bts_serve sees the port busy, stands down, and the BROKEN server (no /api routes)
REM keeps serving -- which silently defeats <TEST>, the signal log and the internodes.
echo [0/3] killing any stale server on 8765...
taskkill /F /IM python.exe  >nul 2>&1
taskkill /F /IM pythonw.exe >nul 2>&1
timeout /t 1 >nul

echo [1/3] refreshing dash.json + mesh_state.json (surfaces, burn, signal log)...
python bts_snapshot.py
if errorlevel 1 (
  echo.
  echo   !! python failed. Is Python on PATH? Try:  py bts_snapshot.py
  echo.
)

echo [2/3] starting bts_serve.py on 127.0.0.1:8765 ...
REM /min so it stays out of the way, but VISIBLE — if it dies, you can see why.
REM (Closing this window stops the server. That is intentional.)
start "BTS dashboard server" /min cmd /c "python bts_serve.py & pause"

REM give the socket a moment to bind before the browser asks for the page
ping -n 3 127.0.0.1 >nul

echo [3/3] opening the dashboard...
start "" "http://localhost:8765/jack_command.html"

echo.
echo Dashboard: http://localhost:8765/jack_command.html
echo   /api/bench    - what ^<TEST^> calls (runs the real mesh probe)
echo   /api/surfaces - disk caps
echo   /api/burn     - live GEM + SGH burn
echo.
echo Leave the "BTS dashboard server" window open. Close it to stop the server.
timeout /t 4 >nul
