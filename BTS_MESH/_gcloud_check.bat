@echo off
set OUT=V:\Research4\Ai\BTS_MESH\_gcloud_check.txt
echo ==== gcloud present? %DATE% %TIME% ==== > "%OUT%"
where gcloud >> "%OUT%" 2>&1
echo   where-exit=%ERRORLEVEL% >> "%OUT%"
echo. >> "%OUT%"
call gcloud --version >> "%OUT%" 2>&1
echo   version-exit=%ERRORLEVEL% >> "%OUT%"
echo. >> "%OUT%"
echo --- any existing ADC / auth on this box? --- >> "%OUT%"
if exist "%APPDATA%\gcloud\application_default_credentials.json" (echo   ADC FILE EXISTS >> "%OUT%") else (echo   no ADC file >> "%OUT%")
call gcloud auth list >> "%OUT%" 2>&1
echo ==== DONE ==== >> "%OUT%"
