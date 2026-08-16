@echo off
set OUT=V:\Research4\Ai\BTS_MESH\_gcheck.txt
echo ==== G: CHECK %DATE% %TIME% ==== > "%OUT%"
echo. >> "%OUT%"
echo --- Get-Volume --- >> "%OUT%"
powershell -NoProfile -Command "Get-Volume | Select-Object DriveLetter,FileSystemLabel,@{n='SizeGB';e={[math]::Round($_.Size/1GB,1)}},@{n='FreeGB';e={[math]::Round($_.SizeRemaining/1GB,1)}},HealthStatus | Format-Table -AutoSize | Out-String -Width 200" >> "%OUT%" 2>&1
echo. >> "%OUT%"
echo --- Get-PhysicalDisk --- >> "%OUT%"
powershell -NoProfile -Command "Get-PhysicalDisk | Select-Object DeviceId,FriendlyName,BusType,@{n='SizeGB';e={[math]::Round($_.Size/1GB,0)}},HealthStatus | Format-Table -AutoSize | Out-String -Width 200" >> "%OUT%" 2>&1
echo. >> "%OUT%"
echo --- G: root listing --- >> "%OUT%"
if exist G:\ (dir G:\ >> "%OUT%" 2>&1) else (echo G: DOES NOT EXIST >> "%OUT%")
echo. >> "%OUT%"
echo --- V: and Research2 sizing ^(the V: collision^) --- >> "%OUT%"
powershell -NoProfile -Command "$r = (Get-ChildItem 'V:\Research4' -Recurse -File -Force -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum); 'Research2 total GB = ' + [math]::Round($r.Sum/1GB,2) + '  (files: ' + $r.Count + ')'" >> "%OUT%" 2>&1
echo. >> "%OUT%"
echo ==== DONE ==== >> "%OUT%"
