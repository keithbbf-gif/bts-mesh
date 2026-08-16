@echo off
set OUT=V:\Research4\Ai\BTS_MESH\_tidy_final_0716.txt
set W=V:\Research4\Ai\PhD2_DATA_ARCHIVE\00_WORKING
echo ==== FINAL TIDYUP %DATE% %TIME% ==== > "%OUT%"
echo. >> "%OUT%"
echo --- 1. MIRROR living docs + today's deliverables -^> 00_WORKING ^(host copy, no FUSE^) --- >> "%OUT%"
for %%F in (
  00_HARVEST_2026-07-16.md
  00_TASK_COMPLETE_KMESH.md
  00_SESSION_WRAPUP_2026-07-16.md
  00_LOOSE_ENDS_2026-07-16.md
  00_FOLDER_ACCESS_RECORD.md
  00_ROLD_COMMANDS_TidyUp_BootUp.md
  00_TOOLS_INDEX.md
  00_NEXT_SESSION_HANDOFF_2026-07-15.md
) do copy /Y "V:\Research4\Ai\%%F" "%W%\%%F" >> "%OUT%" 2>&1
copy /Y "V:\Research4\Ai\BTS_MESH\KMESH_NETWORK_MAP_2026-07-16.png" "%W%\KMESH_NETWORK_MAP_2026-07-16.png" >> "%OUT%" 2>&1
copy /Y "V:\Research4\Ai\BTS_MESH\CREDIT_RECONCILED_2026-07-16.md"  "%W%\CREDIT_RECONCILED_2026-07-16.md" >> "%OUT%" 2>&1
copy /Y "V:\Research4\Ai\BTS_MESH\TB1_DOM_PROVEN_2026-07-16.md"     "%W%\TB1_DOM_PROVEN_2026-07-16.md" >> "%OUT%" 2>&1
echo. >> "%OUT%"

echo --- 2. VERIFY the mirror by MD5 ^(a publish is not a sync^) --- >> "%OUT%"
powershell -NoProfile -Command "$p=@('00_HARVEST_2026-07-16.md','00_TASK_COMPLETE_KMESH.md','00_SESSION_WRAPUP_2026-07-16.md','00_ROLD_COMMANDS_TidyUp_BootUp.md','00_TOOLS_INDEX.md','00_FOLDER_ACCESS_RECORD.md'); $bad=0; foreach($f in $p){ $a='V:\Research4\Ai\'+$f; $b='V:\Research4\Ai\PhD2_DATA_ARCHIVE\00_WORKING\'+$f; $ha=(Get-FileHash $a -Algorithm MD5 -EA SilentlyContinue).Hash; $hb=(Get-FileHash $b -Algorithm MD5 -EA SilentlyContinue).Hash; if($ha -eq $hb){'{0,-42} MATCH' -f $f}else{$bad++;'{0,-42} *** MISMATCH ***' -f $f} }; ''; 'BAD = '+$bad" >> "%OUT%" 2>&1
echo. >> "%OUT%"

echo --- 3. NEGATIVE CONTROL ^(the check must be able to FAIL^) --- >> "%OUT%"
powershell -NoProfile -Command "$a='V:\Research4\Ai\00_HARVEST_2026-07-16.md'; $b='V:\Research4\Ai\00_TOOLS_INDEX.md'; $v = if((Get-FileHash $a -Algorithm MD5).Hash -eq (Get-FileHash $b -Algorithm MD5).Hash){'MATCH (BAD - check is blind!)'}else{'MISMATCH (correct - it can detect a difference)'}; 'HARVEST vs TOOLS_INDEX -> '+$v" >> "%OUT%" 2>&1
echo. >> "%OUT%"

echo --- 4. TOOLS_REGISTRY still parses ^(host python = ground truth^) --- >> "%OUT%"
python -c "import json;d=json.load(open(r'V:\Research4\Ai\BTS_MESH\TOOLS_REGISTRY.json',encoding='utf-8'));print('   PARSE OK - tools:',len(d['tools']))" >> "%OUT%" 2>&1
echo. >> "%OUT%"

echo --- 5. refresh meters + snapshot so the published dash carries today's numbers --- >> "%OUT%"
cd /d V:\Research4\Ai\BTS_MESH
python bts_meters.py > nul 2>&1
echo    meters exit=%ERRORLEVEL% >> "%OUT%"
echo. >> "%OUT%"

echo ==== MIRROR DONE - launching R2 publish ==== >> "%OUT%"
type "%OUT%"
start "" "D:\R2Cloner\Publish-to-R2_KEYED.bat"
