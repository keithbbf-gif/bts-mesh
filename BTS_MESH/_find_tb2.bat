@echo off
REM Fast, TARGETED TeraBox probe. No full-drive walk, no recursive HKCU scan (my first version hung
REM on exactly that). Writes _terabox_probe2.txt. ~3 seconds.
setlocal
set "OUT=%~dp0_terabox_probe2.txt"
> "%OUT%" echo ===== TERABOX PROBE 2  %DATE% %TIME% =====

>> "%OUT%" echo.
>> "%OUT%" echo --- [1] RUNNING PROCESSES (any name containing tera/dubox/flextech) ---
tasklist 2>nul | findstr /I "tera dubox flextech" >> "%OUT%" 2>&1
if errorlevel 1 >> "%OUT%" echo   NONE RUNNING

>> "%OUT%" echo.
>> "%OUT%" echo --- [2] START MENU SHORTCUTS (where an installed app announces itself) ---
dir /b /s "%ProgramData%\Microsoft\Windows\Start Menu\Programs\*tera*" 2>nul >> "%OUT%"
dir /b /s "%APPDATA%\Microsoft\Windows\Start Menu\Programs\*tera*" 2>nul >> "%OUT%"

>> "%OUT%" echo.
>> "%OUT%" echo --- [3] PROGRAM FILES / LOCALAPPDATA (top level only) ---
dir /b "%ProgramFiles%\*tera*" 2>nul >> "%OUT%"
dir /b "%ProgramFiles(x86)%\*tera*" 2>nul >> "%OUT%"
dir /b "%LOCALAPPDATA%\*tera*" 2>nul >> "%OUT%"
dir /b "%LOCALAPPDATA%\Programs\*tera*" 2>nul >> "%OUT%"
dir /b "%APPDATA%\*tera*" 2>nul >> "%OUT%"

>> "%OUT%" echo.
>> "%OUT%" echo --- [4] LIKELY SYNC/DOWNLOAD FOLDERS ---
for %%D in (
  "%USERPROFILE%\TeraBox"
  "%USERPROFILE%\Documents\TeraBox"
  "%USERPROFILE%\Downloads\TeraBox"
  "%USERPROFILE%\TeraBox Download"
  "%USERPROFILE%\TeraBoxDownload"
  "C:\TeraBox" "D:\TeraBox"
) do if exist "%%~D" >> "%OUT%" echo   FOUND: %%~D

>> "%OUT%" echo.
>> "%OUT%" echo --- [5] UNINSTALL REGISTRY (single non-recursive sweep of DisplayName) ---
reg query "HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall" /s /v DisplayName 2>nul | findstr /I "tera" >> "%OUT%" 2>&1
reg query "HKCU\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall" /s /v DisplayName 2>nul | findstr /I "tera" >> "%OUT%" 2>&1
reg query "HKLM\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall" /s /v DisplayName 2>nul | findstr /I "tera" >> "%OUT%" 2>&1

>> "%OUT%" echo.
>> "%OUT%" echo ===== END =====
endlocal
