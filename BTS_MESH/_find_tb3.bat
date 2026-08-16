@echo off
REM TeraBox probe 3 — Cowork 2026-07-15.
REM WHY: probe 2 only searched for "*tera*" in paths/registry. TeraBox was formerly DUBOX, the
REM vendor is FLEXTECH, and the sync client may register under either — or under a generic name.
REM Keith: "You can use it just like OneDrive or GDX." If a native client is on this box, it will
REM show up under one of these aliases or as a sync folder with a desktop.ini / sync database.
setlocal
set "OUT=%~dp0_terabox_probe3.txt"
> "%OUT%" echo ===== TERABOX PROBE 3 (aliases: tera / dubox / flextech / nephogram) %DATE% %TIME% =====

>> "%OUT%" echo.
>> "%OUT%" echo --- [1] ALL uninstall DisplayNames (dump; we grep ourselves) ---
reg query "HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall" /s /v DisplayName 2>nul | findstr /I "tera dubox flex nepho box cloud drive sync" >> "%OUT%" 2>&1
reg query "HKCU\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall" /s /v DisplayName 2>nul | findstr /I "tera dubox flex nepho box cloud drive sync" >> "%OUT%" 2>&1
reg query "HKLM\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall" /s /v DisplayName 2>nul | findstr /I "tera dubox flex nepho box cloud drive sync" >> "%OUT%" 2>&1

>> "%OUT%" echo.
>> "%OUT%" echo --- [2] Program Files / LocalAppData / AppData top level, ALL aliases ---
for %%A in (tera dubox flex nepho) do (
  dir /b "%ProgramFiles%\*%%A*" 2>nul >> "%OUT%"
  dir /b "%ProgramFiles(x86)%\*%%A*" 2>nul >> "%OUT%"
  dir /b "%LOCALAPPDATA%\*%%A*" 2>nul >> "%OUT%"
  dir /b "%LOCALAPPDATA%\Programs\*%%A*" 2>nul >> "%OUT%"
  dir /b "%APPDATA%\*%%A*" 2>nul >> "%OUT%"
)

>> "%OUT%" echo.
>> "%OUT%" echo --- [3] EVERY process with a window (so we can eyeball an odd name) ---
tasklist /FI "STATUS eq RUNNING" 2>nul | findstr /I "tera dubox flex nepho sync cloud" >> "%OUT%" 2>&1
if errorlevel 1 >> "%OUT%" echo   no alias matches running

>> "%OUT%" echo.
>> "%OUT%" echo --- [4] SIDEBAR / NAMESPACE entries (how OneDrive+Drive appear in Explorer) ---
reg query "HKCU\SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\Desktop\NameSpace" /s 2>nul | findstr /I "tera dubox drive box" >> "%OUT%" 2>&1

>> "%OUT%" echo.
>> "%OUT%" echo --- [5] Any folder named *TeraBox*/*Dubox* directly under the user profile + drive roots ---
dir /b /ad "%USERPROFILE%\*tera*" 2>nul >> "%OUT%"
dir /b /ad "%USERPROFILE%\*dubox*" 2>nul >> "%OUT%"
dir /b /ad "C:\*tera*" 2>nul >> "%OUT%"
dir /b /ad "D:\*tera*" 2>nul >> "%OUT%"

>> "%OUT%" echo.
>> "%OUT%" echo --- [6] What the Chrome App actually is ---
dir /b "%APPDATA%\Microsoft\Windows\Start Menu\Programs\Chrome Apps" 2>nul >> "%OUT%"

>> "%OUT%" echo.
>> "%OUT%" echo ===== END =====
endlocal
