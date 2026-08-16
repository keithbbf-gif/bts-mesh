@echo off
REM ===================================================================================
REM  _find_terabox.bat — locate the TeraBox PC client + its sync/download folder.
REM  Cowork, 2026-07-15. Writes findings to _terabox_probe.txt for Cowork to read.
REM
REM  WHY A BAT: Keith's standing rule (2026-07-15) — "Do not ask me to check anything
REM  or run anything, only ever ask for PERMS or API keys." Cowork has Run at full tier,
REM  so Cowork finds this itself. The bat exists because the Linux sandbox cannot see
REM  unmounted Windows paths, and request_access could not resolve the app name.
REM ===================================================================================
setlocal enabledelayedexpansion
set "OUT=%~dp0_terabox_probe.txt"
> "%OUT%" echo ===== TERABOX PROBE  %DATE% %TIME% =====

>> "%OUT%" echo.
>> "%OUT%" echo --- [1] RUNNING PROCESSES matching *tera* ---
tasklist /FO LIST 2>nul | findstr /I "tera" >> "%OUT%" 2>&1
if errorlevel 1 >> "%OUT%" echo   (none running)

>> "%OUT%" echo.
>> "%OUT%" echo --- [2] INSTALL LOCATION from registry (uninstall keys) ---
for %%K in (
  "HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"
  "HKLM\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"
  "HKCU\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"
) do (
  reg query %%K /s /f "TeraBox" /t REG_SZ 2>nul | findstr /I "DisplayName InstallLocation UninstallString" >> "%OUT%" 2>&1
)

>> "%OUT%" echo.
>> "%OUT%" echo --- [3] ANY TeraBox key under HKCU\SOFTWARE ---
reg query "HKCU\SOFTWARE" /s /f "terabox" 2>nul | findstr /I "terabox" >> "%OUT%" 2>&1
if errorlevel 1 >> "%OUT%" echo   (no HKCU keys)

>> "%OUT%" echo.
>> "%OUT%" echo --- [4] COMMON FOLDER LOCATIONS (existence test) ---
for %%D in (
  "%USERPROFILE%\TeraBox"
  "%USERPROFILE%\Documents\TeraBox"
  "%USERPROFILE%\Downloads\TeraBox"
  "%USERPROFILE%\TeraBox Download"
  "C:\TeraBox"
  "D:\TeraBox"
  "%LOCALAPPDATA%\TeraBox"
  "%LOCALAPPDATA%\terabox"
  "%APPDATA%\TeraBox"
  "%PROGRAMFILES%\TeraBox"
  "%PROGRAMFILES(X86)%\TeraBox"
) do (
  if exist "%%~D" ( >> "%OUT%" echo   FOUND: %%~D ) else ( >> "%OUT%" echo   -    : %%~D )
)

>> "%OUT%" echo.
>> "%OUT%" echo --- [5] BRUTE SCAN: any dir named *terabox* on C: and D: (top 3 levels) ---
for %%R in (C D) do (
  if exist %%R:\ (
    dir /b /s /ad "%%R:\*terabox*" 2>nul >> "%OUT%"
  )
)

>> "%OUT%" echo.
>> "%OUT%" echo --- [6] EXE LOCATIONS ---
dir /b /s "C:\Program Files\*terabox*.exe" 2>nul >> "%OUT%"
dir /b /s "C:\Program Files (x86)\*terabox*.exe" 2>nul >> "%OUT%"
dir /b /s "%LOCALAPPDATA%\*terabox*.exe" 2>nul >> "%OUT%"

>> "%OUT%" echo.
>> "%OUT%" echo ===== END. Cowork reads this file; nothing here is sent anywhere. =====
endlocal
