@echo off
REM ============================================================================
REM BUILD_SEC_JUDGE.bat  --  dispatch the SEC six-factor judging app to GW.
REM Created 2026-07-26 by Cowork.
REM
REM WHY A .BAT: the Linux sandbox caps every shell call at 45 s. GW generates at
REM ~30 tokens/sec, so a full single-file app (~20k tokens) needs ~10 minutes of
REM wall time. Native Windows python has no such cap. This is the ROLD's
REM "long jobs run in the background, Keith does not wait" pattern.
REM
REM Safe to re-run: it overwrites the artifact and appends to the log.
REM ============================================================================
setlocal
set PYTHONIOENCODING=utf-8
set MESH=V:\Research4\Ai\BTS_MESH
set WORK=V:\Research4\Ai\PhD2_DATA_ARCHIVE\00_WORKING
set SECD=%WORK%\ch4_verify_SEC
set LOG=%MESH%\gw_build.log

cd /d "%MESH%"

echo. >> "%LOG%"
echo ================================================== >> "%LOG%"
echo [%DATE% %TIME%] GW build start: SEC_JUDGE.html >> "%LOG%"

REM Find a python. py.exe launcher first, then plain python.
where py >nul 2>&1 && (set PY=py -3) || (set PY=python)

%PY% "%MESH%\bts_gw.py" ^
  --spec "%WORK%\GBW_BUILD_SEC_JUDGE_2026-07-26.md" ^
  --out "%SECD%\SEC_JUDGE.html" ^
  --fence html ^
  --timeout 900 ^
  --max-tokens 64000 >> "%LOG%" 2>&1

set RC=%ERRORLEVEL%
echo [%DATE% %TIME%] GW build exit=%RC% >> "%LOG%"

if %RC%==0 (
  echo [%DATE% %TIME%] artifact: >> "%LOG%"
  dir "%SECD%\SEC_JUDGE.html" >> "%LOG%" 2>&1
  echo BUILD OK - see %SECD%\SEC_JUDGE.html
) else (
  echo BUILD FAILED rc=%RC% - see %LOG%
)

REM Leave the window up long enough to read, then close on its own.
timeout /t 20 >nul
endlocal
