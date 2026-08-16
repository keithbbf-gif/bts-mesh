@echo off
set OUT=V:\Research4\Ai\BTS_MESH\_move_audit.txt
echo ==== MOVE-TO-NVMe AUDIT %DATE% %TIME% ==== > "%OUT%"
echo  Question: move ODX + GDX(local) + Research2 to V: (ADATA NVMe, 447.1 GB)? >> "%OUT%"
echo. >> "%OUT%"

echo --- 1. WHAT ARE WE ACTUALLY MOVING? (sizes, measured) --- >> "%OUT%"
powershell -NoProfile -Command ^
 "$t=@{'Research2'='V:\Research4'; 'ODX (BTS_ODX)'='D:\ODX\OneDrive\BTS_ODX'; 'ODX (whole OneDrive)'='D:\ODX\OneDrive'; 'GDX local'='X:\My Drive\BTS_SGH_Handoff'};" ^
 "$sum=0; foreach($k in $t.Keys){ $p=$t[$k]; if(Test-Path $p){ $m=(Get-ChildItem $p -Recurse -File -Force -EA SilentlyContinue | Measure-Object -Property Length -Sum); $gb=[math]::Round($m.Sum/1GB,2); if($k -ne 'ODX (whole OneDrive)'){$sum+=$gb}; '{0,-24} {1,8} GB   {2,7} files' -f $k,$gb,$m.Count } else { '{0,-24} NOT PRESENT' -f $k } };" ^
 "''; 'SUBTOTAL to move (Research2 + BTS_ODX + GDX) = ' + [math]::Round($sum,2) + ' GB'" >> "%OUT%" 2>&1
echo. >> "%OUT%"

echo --- 2. V: CAPACITY REALITY --- >> "%OUT%"
powershell -NoProfile -Command ^
 "$v=Get-Volume -DriveLetter V; $tot=[math]::Round($v.Size/1GB,1); $free=[math]::Round($v.SizeRemaining/1GB,1);" ^
 "'V: total {0} GB · free {1} GB' -f $tot,$free;" ^
 "'SSD headroom rule: keep under ~85%% or sustained write collapses. Usable = ' + [math]::Round($tot*0.85,1) + ' GB'" >> "%OUT%" 2>&1
echo. >> "%OUT%"

echo --- 3. THE REAL BLOCKER: how many things hardcode V:\Research4 ? --- >> "%OUT%"
powershell -NoProfile -Command ^
 "$pat='V:\\Research4';" ^
 "$files = Get-ChildItem 'V:\Research4\Ai' -Recurse -File -Include *.py,*.bat,*.vbs,*.json,*.html,*.md -EA SilentlyContinue;" ^
 "$hits = $files | Select-String -Pattern ([regex]::Escape('V:\Research4')) -SimpleMatch -EA SilentlyContinue;" ^
 "'TOTAL hardcoded ''V:\Research4'' refs under Ai\ : ' + $hits.Count;" ^
 "'   in ' + ($hits | Select-Object -ExpandProperty Path -Unique).Count + ' distinct files';" ^
 "''; 'BY TYPE:';" ^
 "$hits | Group-Object {[IO.Path]::GetExtension($_.Path)} | Sort-Object Count -Desc | ForEach-Object { '   {0,-6} {1,5} refs' -f $_.Name,$_.Count };" ^
 "''; 'THE CODE THAT BREAKS FIRST (py/bat/vbs only):';" ^
 "$hits | Where-Object { $_.Path -match '\.(py|bat|vbs)$' } | Group-Object Path | Sort-Object Count -Desc | Select-Object -First 12 | ForEach-Object { '   {0,4}x  {1}' -f $_.Count,[IO.Path]::GetFileName($_.Name) }" >> "%OUT%" 2>&1
echo. >> "%OUT%"

echo --- 4. Desktop launchers + scheduled tasks that point at D: --- >> "%OUT%"
powershell -NoProfile -Command "Get-ChildItem 'C:\Users\Papa\OneDrive\Desktop\*.vbs' -EA SilentlyContinue | ForEach-Object { $h=(Select-String -Path $_.FullName -Pattern ([regex]::Escape('V:\Research4')) -SimpleMatch -EA SilentlyContinue).Count; '   {0,-34} {1} refs' -f $_.Name,$h }" >> "%OUT%" 2>&1
powershell -NoProfile -Command "'   R2 publish bat:'; (Select-String -Path 'D:\R2Cloner\Publish-to-R2_KEYED.bat' -Pattern ([regex]::Escape('V:\Research4')) -SimpleMatch -EA SilentlyContinue).Count.ToString() + ' refs (SRC paths)'" >> "%OUT%" 2>&1
echo. >> "%OUT%"
echo ==== DONE ==== >> "%OUT%"
type "%OUT%"
