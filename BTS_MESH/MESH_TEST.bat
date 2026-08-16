@echo off
REM Full KMesh test — every node, every surface, with negative controls.
REM Native because the sandbox is egress-blocked from googleapis and capped at 45 s per call.
REM py -3.13: pydrive2 / OAuth stack live there; py -3 is 3.14 on this box.
setlocal
set PYTHONIOENCODING=utf-8
set MESH=V:\Research4\Ai\BTS_MESH
cd /d "%MESH%"
echo.
echo   Running the full mesh test. Node calls take a few minutes.
echo.
py -3.13 "%MESH%\mesh_test.py" 2>&1
echo.
echo   exit=%ERRORLEVEL%
echo.
pause
endlocal
