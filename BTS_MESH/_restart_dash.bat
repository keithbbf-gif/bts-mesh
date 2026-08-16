@echo off
REM ===================================================================================
REM  _restart_dash.bat  —  restart bts_serve.py so it picks up EDITED python modules.
REM  Cowork, 2026-07-15.
REM
REM  WHY THIS EXISTS:
REM    bts_serve.py is a LONG-RUNNING process. Python caches modules in sys.modules, so
REM    `import bts_snapshot` inside a request handler is a no-op after the first call —
REM    it binds the ALREADY-LOADED module. Editing bts_snapshot.py / bts_policy.py /
REM    bts_bench.py therefore changes NOTHING on screen until the process restarts.
REM    Proven 2026-07-15: /api/bench returned 200, ran the real probes for 15s, rewrote
REM    dash.json with a fresh timestamp — and still emitted the OLD note text, because
REM    the old code was still in memory. The dashboard was faithfully rendering a
REM    corrected file's stale twin.
REM
REM    bts_serve has no --stop: if it sees itself on the port it prints
REM    "already running - nothing to do" and exits. So the VBS cannot restart it either.
REM    The process must be killed first. Hence this.
REM
REM  SAFETY: this kills ONLY the PID that is LISTENING on 8765. It does not
REM  `taskkill /IM pythonw.exe`, which would take out every other python on the box.
REM ===================================================================================
setlocal
cd /d "%~dp0"

echo.
echo  === restarting bts_serve.py on port 8765 ===
echo.

set "FOUND="
for /f "tokens=5" %%P in ('netstat -ano ^| findstr /R /C:":8765 .*LISTENING"') do (
    if not "%%P"=="0" (
        echo   killing PID %%P  (listener on :8765)
        taskkill /F /PID %%P >nul 2>&1
        set "FOUND=1"
    )
)
if not defined FOUND echo   nothing was listening on :8765

timeout /t 2 /nobreak >nul

echo   relaunching bts_serve.py (hidden, pythonw)...
where pythonw >nul 2>&1
if %errorlevel%==0 (
    start "" pythonw "bts_serve.py"
) else (
    start "" /min python "bts_serve.py"
)

timeout /t 3 /nobreak >nul

echo.
echo   verifying /api/state ...
curl -s --max-time 5 "http://127.0.0.1:8765/api/state" 2>nul || echo   (curl unavailable - open the dashboard and check)
echo.
echo  Reload http://localhost:8765/jack_command.html and press ^<TEST^>.
echo  The GEM / policy / credit notes should now say what the corrected code says.
echo.
endlocal
