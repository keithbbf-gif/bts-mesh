@echo off
set OUT=V:\Research4\Ai\BTS_MESH\_where_odx_gdx.txt
echo ==== WHERE ARE ODX AND GDX, REALLY? %DATE% %TIME% ==== > "%OUT%"
echo. >> "%OUT%"

echo --- 1. ODX / OneDrive: the ROOT the client is actually syncing --- >> "%OUT%"
powershell -NoProfile -Command "Get-ItemProperty 'HKCU:\Software\Microsoft\OneDrive\Accounts\*' -EA SilentlyContinue | Select-Object PSChildName,UserFolder,UserEmail | Format-List | Out-String -Width 200" >> "%OUT%" 2>&1
powershell -NoProfile -Command "'  env OneDrive        = ' + $env:OneDrive; '  env OneDriveConsumer= ' + $env:OneDriveConsumer" >> "%OUT%" 2>&1
echo. >> "%OUT%"

echo --- 2. GDX / Google Drive: which letter, and is it a REAL disk or a virtual mount? --- >> "%OUT%"
powershell -NoProfile -Command "Get-PSDrive -PSProvider FileSystem | Select-Object Name,Root,@{n='UsedGB';e={if($_.Used){[math]::Round($_.Used/1GB,1)}}},@{n='FreeGB';e={if($_.Free){[math]::Round($_.Free/1GB,1)}}},DisplayRoot | Format-Table -AutoSize | Out-String -Width 200" >> "%OUT%" 2>&1
powershell -NoProfile -Command "Get-Volume | Select-Object DriveLetter,FileSystemLabel,FileSystem,DriveType,@{n='SizeGB';e={[math]::Round($_.Size/1GB,1)}} | Format-Table -AutoSize | Out-String -Width 200" >> "%OUT%" 2>&1
echo. >> "%OUT%"

echo --- 3. THE POINT: are the files ON DISK, or cloud-only placeholders? --- >> "%OUT%"
echo    (FileAttributes 'Offline'/'RecallOnDataAccess' = the bytes are NOT here) >> "%OUT%"
powershell -NoProfile -Command ^
 "$t=@{ 'ODX  BTS_ODX'='D:\ODX\OneDrive\BTS_ODX'; 'ODX  OneDrive root'='D:\ODX\OneDrive'; 'GDX  handoff'='X:\My Drive\BTS_SGH_Handoff' };" ^
 "foreach($k in $t.Keys){ $p=$t[$k];" ^
 "  if(-not (Test-Path $p)){ '{0,-20} NOT PRESENT  {1}' -f $k,$p; continue }" ^
 "  $f=Get-ChildItem $p -Recurse -File -Force -EA SilentlyContinue;" ^
 "  $on =($f | Where-Object { -not ($_.Attributes -band [IO.FileAttributes]::Offline) });" ^
 "  $off=($f | Where-Object {      ($_.Attributes -band [IO.FileAttributes]::Offline) });" ^
 "  $onGB=[math]::Round((($on|Measure-Object Length -Sum).Sum)/1GB,2);" ^
 "  $allGB=[math]::Round((($f|Measure-Object Length -Sum).Sum)/1GB,2);" ^
 "  '{0,-20} {1}' -f $k,$p;" ^
 "  '                     files {0,6} | ON DISK {1,5} | cloud-only {2,5} | bytes-on-disk {3} GB | logical {4} GB' -f $f.Count,$on.Count,$off.Count,$onGB,$allGB } " >> "%OUT%" 2>&1
echo. >> "%OUT%"

echo --- 4. What does the OneDrive client say its state is? --- >> "%OUT%"
powershell -NoProfile -Command "$p='D:\ODX\OneDrive'; if(Test-Path $p){ $i=Get-Item $p -Force; '  OneDrive root attrs: ' + $i.Attributes } ; 'ReparsePoint/SparseFile on the root = Files-On-Demand is ON'" >> "%OUT%" 2>&1
powershell -NoProfile -Command "Get-Process OneDrive,GoogleDriveFS -EA SilentlyContinue | Select-Object Name,Id,@{n='WS_MB';e={[math]::Round($_.WorkingSet/1MB)}} | Format-Table -AutoSize | Out-String -Width 120" >> "%OUT%" 2>&1
echo. >> "%OUT%"
echo ==== DONE ==== >> "%OUT%"
type "%OUT%"
