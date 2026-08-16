@echo off
cd /d V:\Research4\Ai\BTS_MESH
if "%~1"=="" (
  python bts_calibrate.py
) else (
  python bts_calibrate.py %*
)
echo.
pause
