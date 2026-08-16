@echo off
REM ============================================================================
REM   >>> KEITH: RIGHT-CLICK THIS FILE -> "Run as administrator" <<<
REM
REM   WHY IT NEEDS ADMIN, AND WHY IT IS MY FAULT IT IS STILL OPEN:
REM   Get-StorageReliabilityCounter (SMART: power-on hours, reallocated sectors, read errors,
REM   temperature) REQUIRES elevation. I ran _drivehealth.bat unelevated on 2026-07-15, every SMART
REM   field came back BLANK, and I reported the drives as "Healthy" on the shallow check — which only
REM   says "the OS can talk to it", not "it is not about to die". That was my bug and it has blocked
REM   the Hitachi decision ever since.
REM
REM   WHAT IT DECIDES:
REM   The 3 TB Hitachi is the proposed home for 100-300 GB of IRREPLACEABLE product photography.
REM   It is ~2012 vintage with UNKNOWN power-on hours. A 14-year-old drive with 60,000 hours and
REM   reallocated sectors is not a photo library, it is a countdown. THIS is the number that decides
REM   whether A2/A7 in 00_TASK_COMPLETE_KMESH go ahead.
REM
REM   It writes  _drivehealth_ELEVATED.txt  next to itself. Nothing is changed, only read.
REM ============================================================================
net session >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
  echo.
  echo   *** NOT ELEVATED — this will produce the SAME blank SMART fields as before. ***
  echo   Close this, RIGHT-CLICK the file, choose "Run as administrator".
  echo.
  pause
  exit /b 1
)

set OUT=%~dp0_drivehealth_ELEVATED.txt
echo ==== DRIVE HEALTH (ELEVATED) %DATE% %TIME% ==== > "%OUT%"
echo. >> "%OUT%"

echo --- 1. EVERY physical disk: identity + bus + health --- >> "%OUT%"
powershell -NoProfile -Command "Get-PhysicalDisk | Select-Object DeviceId,FriendlyName,SerialNumber,BusType,MediaType,@{n='SizeGB';e={[math]::Round($_.Size/1GB)}},HealthStatus,OperationalStatus | Format-Table -AutoSize | Out-String -Width 220" >> "%OUT%" 2>&1
echo. >> "%OUT%"

echo --- 2. SMART / RELIABILITY — THE POINT OF RUNNING THIS ELEVATED --- >> "%OUT%"
echo     PowerOnHours is the number that decides the Hitachi. >> "%OUT%"
powershell -NoProfile -Command ^
 "foreach($d in Get-PhysicalDisk){" ^
 "  $c = $d | Get-StorageReliabilityCounter -EA SilentlyContinue;" ^
 "  '';" ^
 "  '  [{0}] {1}  ({2}, {3} GB)' -f $d.DeviceId,$d.FriendlyName,$d.BusType,[math]::Round($d.Size/1GB);" ^
 "  if($c){" ^
 "    '      PowerOnHours      : {0}{1}' -f $c.PowerOnHours, $(if($c.PowerOnHours){' (= ' + [math]::Round($c.PowerOnHours/8760,1) + ' YEARS powered on)'}else{' <-- still blank: this disk does not report it'});" ^
 "    '      Temperature       : {0} C   (max {1})' -f $c.Temperature,$c.TemperatureMax;" ^
 "    '      ReadErrorsTotal   : {0}   uncorrected {1}' -f $c.ReadErrorsTotal,$c.ReadErrorsUncorrected;" ^
 "    '      WriteErrorsTotal  : {0}   uncorrected {1}' -f $c.WriteErrorsTotal,$c.WriteErrorsUncorrected;" ^
 "    '      Wear              : {0}' -f $c.Wear;" ^
 "    '      StartStopCycles   : {0}' -f $c.StartStopCycleCount;" ^
 "  } else { '      *** no reliability counters — USB bridges often hide SMART from Windows ***' } }" >> "%OUT%" 2>&1
echo. >> "%OUT%"

echo --- 3. Does the disk itself predict failure? --- >> "%OUT%"
powershell -NoProfile -Command "Get-WmiObject -Namespace root\wmi -Class MSStorageDriver_FailurePredictStatus -EA SilentlyContinue | Select-Object InstanceName,PredictFailure,Reason | Format-Table -AutoSize | Out-String -Width 200" >> "%OUT%" 2>&1
echo   (PredictFailure = True on ANY row means replace that drive now.) >> "%OUT%"
echo. >> "%OUT%"

echo --- 4. Volumes + free space --- >> "%OUT%"
powershell -NoProfile -Command "Get-Volume | Where-Object DriveLetter | Select-Object DriveLetter,FileSystemLabel,@{n='SizeGB';e={[math]::Round($_.Size/1GB,1)}},@{n='FreeGB';e={[math]::Round($_.SizeRemaining/1GB,1)}},HealthStatus | Format-Table -AutoSize | Out-String -Width 200" >> "%OUT%" 2>&1
echo. >> "%OUT%"

echo ==== DONE — read-only. Nothing was changed. ==== >> "%OUT%"
echo. >> "%OUT%"
echo   HOW TO READ IT: >> "%OUT%"
echo     PowerOnHours ^> ~45,000 (5+ yrs) on the Hitachi  -^> do NOT trust it with the only copy. >> "%OUT%"
echo     ANY reallocated/uncorrected errors               -^> do NOT trust it at all. >> "%OUT%"
echo     Blank on a USB drive                             -^> the enclosure hides SMART; connect it >> "%OUT%"
echo                                                          by SATA to read it honestly. >> "%OUT%"
type "%OUT%"
echo.
echo   Wrote: %OUT%
echo.
pause
