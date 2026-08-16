@echo off
REM sysinfo probe — Cowork 2026-07-15. For the NVMe purchase decision.
REM Need: motherboard model (decides M.2 slot count + PCIe gen), CPU (decides PCIe lanes),
REM current drives (what is already occupying slots), and free slots.
setlocal
set "OUT=%~dp0_sysinfo.txt"
> "%OUT%" echo ===== SYSINFO  %DATE% %TIME% =====

>> "%OUT%" echo.
>> "%OUT%" echo --- MOTHERBOARD (decides how many M.2 slots and which PCIe gen) ---
powershell -NoProfile -Command "Get-CimInstance Win32_BaseBoard | Select-Object Manufacturer,Product,Version,SerialNumber | Format-List" >> "%OUT%" 2>&1

>> "%OUT%" echo.
>> "%OUT%" echo --- SYSTEM / BIOS ---
powershell -NoProfile -Command "Get-CimInstance Win32_ComputerSystem | Select-Object Manufacturer,Model,SystemFamily,TotalPhysicalMemory | Format-List; Get-CimInstance Win32_BIOS | Select-Object Manufacturer,SMBIOSBIOSVersion,ReleaseDate | Format-List" >> "%OUT%" 2>&1

>> "%OUT%" echo.
>> "%OUT%" echo --- CPU (PCIe lane budget) ---
powershell -NoProfile -Command "Get-CimInstance Win32_Processor | Select-Object Name,NumberOfCores,NumberOfLogicalProcessors,MaxClockSpeed | Format-List" >> "%OUT%" 2>&1

>> "%OUT%" echo.
>> "%OUT%" echo --- PHYSICAL DISKS (what is installed now) ---
powershell -NoProfile -Command "Get-PhysicalDisk | Select-Object DeviceId,FriendlyName,MediaType,BusType,@{n='SizeGB';e={[math]::Round($_.Size/1GB,1)}},HealthStatus | Format-Table -AutoSize" >> "%OUT%" 2>&1

>> "%OUT%" echo.
>> "%OUT%" echo --- DISK DRIVES detail (model + interface) ---
powershell -NoProfile -Command "Get-CimInstance Win32_DiskDrive | Select-Object Index,Model,InterfaceType,@{n='SizeGB';e={[math]::Round($_.Size/1GB,1)}},Partitions | Format-Table -AutoSize" >> "%OUT%" 2>&1

>> "%OUT%" echo.
>> "%OUT%" echo --- NVMe / storage controllers (shows how many M.2 are POPULATED) ---
powershell -NoProfile -Command "Get-PnpDevice -Class 'SCSIAdapter','HDC' -Status OK | Select-Object FriendlyName,InstanceId | Format-Table -AutoSize -Wrap" >> "%OUT%" 2>&1

>> "%OUT%" echo.
>> "%OUT%" echo --- VOLUMES ---
powershell -NoProfile -Command "Get-Volume | Where-Object {$_.DriveLetter} | Select-Object DriveLetter,FileSystemLabel,@{n='SizeGB';e={[math]::Round($_.Size/1GB,1)}},@{n='FreeGB';e={[math]::Round($_.SizeRemaining/1GB,1)}} | Format-Table -AutoSize" >> "%OUT%" 2>&1

>> "%OUT%" echo.
>> "%OUT%" echo ===== END =====
endlocal
