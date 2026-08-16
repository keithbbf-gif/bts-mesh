@echo off
set OUT=V:\Research4\Ai\BTS_MESH\_migrate_step34_final.txt
echo ==== STEP 3 FIX + STEP 4 EXTERNAL REFS %DATE% %TIME% ==== > "%OUT%"
echo. >> "%OUT%"

cd /d V:\Research4\Ai\BTS_MESH
echo --- 3e. FIX what the verify caught --- >> "%OUT%"
python _migrate_fix.py >> "%OUT%" 2>&1
echo. >> "%OUT%"

echo --- 3f. RE-VERIFY (must now be 0 live refs) --- >> "%OUT%"
python _migrate_verify.py >> "%OUT%" 2>&1
echo. >> "%OUT%"

echo ================================================================ >> "%OUT%"
echo   STEP 4 — EXTERNAL REFS (things OUTSIDE the tree that point INTO it) >> "%OUT%"
echo   These are staged as .NEW files. NOTHING is switched until Keith renames >> "%OUT%"
echo   V:\Research4 -^> D:\Research3 at the next session start. >> "%OUT%"
echo ================================================================ >> "%OUT%"
echo. >> "%OUT%"

echo --- 4a. WHO points at V:\Research4 from outside? --- >> "%OUT%"
powershell -NoProfile -Command "$t=@('C:\Users\Papa\OneDrive\Desktop\KDash.vbs','C:\Users\Papa\OneDrive\Desktop\JDash.vbs','C:\Users\Papa\OneDrive\Desktop\Jack''s Mesh Command.vbs','D:\R2Cloner\Publish-to-R2_KEYED.bat','D:\R2Cloner\r2.bat'); foreach($p in $t){ if(Test-Path $p){ $n=(Select-String -Path $p -Pattern 'V:\\Research4' -SimpleMatch -EA SilentlyContinue).Count; '{0,-46} {1,3} refs' -f (Split-Path $p -Leaf),$n } else { '{0,-46} not present' -f (Split-Path $p -Leaf) } }" >> "%OUT%" 2>&1
echo. >> "%OUT%"

echo --- 4b. SCHEDULED TASKS that mention the tree --- >> "%OUT%"
powershell -NoProfile -Command "Get-ChildItem 'C:\Users\Papa\Claude\Scheduled' -Recurse -Filter *.md -EA SilentlyContinue | ForEach-Object { $n=(Select-String -Path $_.FullName -Pattern 'V:\\Research4' -SimpleMatch -EA SilentlyContinue).Count; if($n -gt 0){ '{0,-46} {1,3} refs' -f $_.Name,$n } }" >> "%OUT%" 2>&1
echo. >> "%OUT%"

echo --- 4c. STAGE the switched copies (.NEW — not live yet) --- >> "%OUT%"
powershell -NoProfile -Command ^
 "$t=@('C:\Users\Papa\OneDrive\Desktop\KDash.vbs','D:\R2Cloner\Publish-to-R2_KEYED.bat');" ^
 "foreach($p in $t){ if(-not (Test-Path $p)){ '  {0} not present' -f $p; continue }" ^
 "  $c=Get-Content $p -Raw;" ^
 "  $n=$c -replace [regex]::Escape('V:\Research4'),'V:\Research4';" ^
 "  $out=$p + '.NEW';" ^
 "  Set-Content -Path $out -Value $n -NoNewline;" ^
 "  $was=([regex]::Matches($c,[regex]::Escape('V:\Research4'))).Count;" ^
 "  $now=([regex]::Matches($n,[regex]::Escape('V:\Research4'))).Count;" ^
 "  '  staged {0,-44} was {1} refs -> {2} left  ({3})' -f (Split-Path $p -Leaf),$was,$now,$out }" >> "%OUT%" 2>&1
echo. >> "%OUT%"
echo   ^>^> .NEW files are STAGED ONLY. Swap them in at cutover, not before: >> "%OUT%"
echo      V:\Research4 is still the LIVE tree until Keith renames it. >> "%OUT%"
echo. >> "%OUT%"
echo ==== DONE ==== >> "%OUT%"
type "%OUT%"
