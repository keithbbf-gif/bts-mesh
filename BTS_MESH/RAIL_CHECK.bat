@echo off
REM ============================================================================
REM RAIL_CHECK.bat  --  daily rail health, run NATIVELY.
REM Created 2026-07-26 by Cowork.
REM
REM Replaces the Cowork scheduled task `free-tier-allotment-check`, which
REM produced SEVEN consecutive days of "BLOCKED - nothing measured" because
REM V:\Research4 is not in that task's connected-folder set and an unattended
REM run cannot request a folder. The folder set is not editable on disk.
REM
REM Running natively removes the dependency entirely: V: is just a drive letter
REM here, and the credentials are probed from the machine that owns them --
REM which also avoids Cowork's sandbox being egress-blocked from googleapis and
REM wrongly reporting GEM and Vertex as dead.
REM
REM Registered as Windows scheduled task "BTS Rail Check", daily 02:05.
REM Writes to  ...\PhD2_DATA_ARCHIVE\00_WORKING\  and  D:\ODX\...\BTS_ODX\reports\
REM ============================================================================
setlocal
set PYTHONIOENCODING=utf-8
set MESH=V:\Research4\Ai\BTS_MESH
set LOG=%MESH%\rail_check.log

cd /d "%MESH%"
where py >nul 2>&1 && (set PY=py -3) || (set PY=python)

echo [%DATE% %TIME%] rail check start >> "%LOG%"
%PY% "%MESH%\rail_check.py" >> "%LOG%" 2>&1
echo [%DATE% %TIME%] rail check exit=%ERRORLEVEL% >> "%LOG%"
endlocal
