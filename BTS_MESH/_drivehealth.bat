@echo off
REM Drive health / SMART sweep — Cowork 2026-07-15.
REM WHY: deciding where 100-300 GB of irreplaceable business photography lives, and whether the
REM ~2012 Hitachi is fit to be its backup. Power-on hours + reallocated sectors + wear decide it.
REM CAVEAT: USB-attached drives often do NOT pass SMART through the bridge chip. Windows may return
REM blanks for D:/G:/L: — that is the bridge hiding it, NOT a healthy drive. Say so; do not call a
REM silent drive healthy.
setlocal
set "OUT=%~dp0_drivehealth.txt"
> "%OUT%" echo ===== DRIVE HEALTH  %DATE% %TIME% =====

>> "%OUT%" echo.
>> "%OUT%" echo --- [1] ALL PHYSICAL DISKS ---
powershell -NoProfile -Command "Get-PhysicalDisk | Sort-Object DeviceId | Select-Object DeviceId,FriendlyName,SerialNumber,MediaType,BusType,@{n='SizeGB';e={[math]::Round($_.Size/1GB,1)}},HealthStatus,OperationalStatus | Format-Table -AutoSize" >> "%OUT%" 2>&1

>> "%OUT%" echo.
>> "%OUT%" echo --- [2] RELIABILITY COUNTERS (power-on hours / temp / errors / wear) ---
>> "%OUT%" echo     Blank rows = the USB bridge is hiding SMART, NOT proof of health.
powershell -NoProfile -Command "Get-PhysicalDisk | Sort-Object DeviceId | ForEach-Object { $d=$_; $c = $d | Get-StorageReliabilityCounter -ErrorAction SilentlyContinue; [PSCustomObject]@{ Id=$d.DeviceId; Name=$d.FriendlyName; Bus=$d.BusType; PowerOnHours=$c.PowerOnHours; Temp_C=$c.Temperature; Wear=$c.Wear; ReadErrUncorr=$c.ReadErrorsUncorrected; WriteErrUncorr=$c.WriteErrorsUncorrected; StartStop=$c.StartStopCycles } } | Format-Table -AutoSize" >> "%OUT%" 2>&1

>> "%OUT%" echo.
>> "%OUT%" echo --- [3] PowerOnHours in YEARS (context for the ~2012 Hitachi decision) ---
powershell -NoProfile -Command "Get-PhysicalDisk | ForEach-Object { $d=$_; $c=$d | Get-StorageReliabilityCounter -ErrorAction SilentlyContinue; if ($c.PowerOnHours) { '{0,-24} {1,8} hrs = {2,6:N2} yrs continuous' -f $d.FriendlyName,$c.PowerOnHours,($c.PowerOnHours/8766) } else { '{0,-24} SMART NOT EXPOSED (bus={1}) - unknown, not healthy' -f $d.FriendlyName,$d.BusType } }" >> "%OUT%" 2>&1

>> "%OUT%" echo.
>> "%OUT%" echo --- [4] LEGACY SMART PREDICT-FAIL (covers some drives the above misses) ---
powershell -NoProfile -Command "Get-CimInstance -Namespace root\wmi -ClassName MSStorageDriver_FailurePredictStatus -ErrorAction SilentlyContinue | Select-Object InstanceName,PredictFailure,Reason | Format-Table -AutoSize -Wrap" >> "%OUT%" 2>&1
powershell -NoProfile -Command "Get-CimInstance -ClassName Win32_DiskDrive | Select-Object Index,Model,SerialNumber,Status,@{n='SizeGB';e={[math]::Round($_.Size/1GB,1)}} | Format-Table -AutoSize" >> "%OUT%" 2>&1

>> "%OUT%" echo.
>> "%OUT%" echo --- [5] NVMe wear detail (C: and V: are the ones that matter for the photo library) ---
powershell -NoProfile -Command "Get-PhysicalDisk | Where-Object {$_.BusType -eq 'NVMe'} | ForEach-Object { $d=$_; $c=$d|Get-StorageReliabilityCounter -ErrorAction SilentlyContinue; '{0}: Wear={1}%  PowerOn={2}h  Temp={3}C  ReadErr={4}  WriteErr={5}' -f $d.FriendlyName,$c.Wear,$c.PowerOnHours,$c.Temperature,$c.ReadErrorsUncorrected,$c.WriteErrorsUncorrected }" >> "%OUT%" 2>&1

>> "%OUT%" echo.
>> "%OUT%" echo --- [6] VOLUMES + free space ---
powershell -NoProfile -Command "Get-Volume | Where-Object {$_.DriveLetter} | Sort-Object DriveLetter | Select-Object DriveLetter,FileSystemLabel,FileSystem,@{n='SizeGB';e={[math]::Round($_.Size/1GB,1)}},@{n='FreeGB';e={[math]::Round($_.SizeRemaining/1GB,1)}},HealthStatus | Format-Table -AutoSize" >> "%OUT%" 2>&1

>> "%OUT%" echo.
>> "%OUT%" echo --- [7] SIZE THE CONTENDERS FOR V: (photo lib vs Research2 - they may not both fit) ---
for %%D in ("V:\Research4" "D:\PhD" "D:\ODX") do (
  >> "%OUT%" echo   sizing %%D ...
  powershell -NoProfile -Command "$p='%%~D'; if (Test-Path $p) { $s=(Get-ChildItem $p -Recurse -Force -File -ErrorAction SilentlyContinue | Measure-Object -Sum Length); '{0,-20} {1,10:N1} GB  ({2:N0} files)' -f $p,($s.Sum/1GB),$s.Count } else { '{0,-20} NOT FOUND' -f $p }" >> "%OUT%" 2>&1
)

>> "%OUT%" echo.
>> "%OUT%" echo ===== END =====
endlocal
