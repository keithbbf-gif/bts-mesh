@echo off
set OUT=V:\Research4\Ai\BTS_MESH\_tidy_0716.txt
echo ==== TIDYUP 2026-07-16 %DATE% %TIME% ==== > "%OUT%"
echo. >> "%OUT%"

echo --- 1. TOOLS_REGISTRY.json validate ^(HOST python = ground truth^) --- >> "%OUT%"
python -c "import json;d=json.load(open(r'V:\Research4\Ai\BTS_MESH\TOOLS_REGISTRY.json',encoding='utf-8'));print('PARSE OK - tools:',len(d['tools']),'updated:',d['_updated']);[print('   -',t['id']) for t in d['tools']]" >> "%OUT%" 2>&1
echo. >> "%OUT%"

echo --- 2. bts_identity self-test --- >> "%OUT%"
python "V:\Research4\Ai\BTS_MESH\bts_identity.py" >> "%OUT%" 2>&1
echo    exit=%ERRORLEVEL% >> "%OUT%"
echo. >> "%OUT%"

echo --- 3. MIRROR living docs -^> PhD2_DATA_ARCHIVE\00_WORKING ^(host copy, no FUSE^) --- >> "%OUT%"
copy /Y "V:\Research4\Ai\00_FOLDER_ACCESS_RECORD.md" "V:\Research4\Ai\PhD2_DATA_ARCHIVE\00_WORKING\00_FOLDER_ACCESS_RECORD.md" >> "%OUT%" 2>&1
copy /Y "V:\Research4\Ai\00_ROLD_COMMANDS_TidyUp_BootUp.md" "V:\Research4\Ai\PhD2_DATA_ARCHIVE\00_WORKING\00_ROLD_COMMANDS_TidyUp_BootUp.md" >> "%OUT%" 2>&1
copy /Y "V:\Research4\Ai\00_TOOLS_INDEX.md" "V:\Research4\Ai\PhD2_DATA_ARCHIVE\00_WORKING\00_TOOLS_INDEX.md" >> "%OUT%" 2>&1
copy /Y "V:\Research4\Ai\00_LOOSE_ENDS_2026-07-16.md" "V:\Research4\Ai\PhD2_DATA_ARCHIVE\00_WORKING\00_LOOSE_ENDS_2026-07-16.md" >> "%OUT%" 2>&1
copy /Y "V:\Research4\Ai\00_NEXT_SESSION_HANDOFF_2026-07-15.md" "V:\Research4\Ai\PhD2_DATA_ARCHIVE\00_WORKING\00_NEXT_SESSION_HANDOFF_2026-07-15.md" >> "%OUT%" 2>&1
echo. >> "%OUT%"

echo --- 4. VERIFY the mirror actually matches ^(size compare^) --- >> "%OUT%"
powershell -NoProfile -Command "$p=@('00_FOLDER_ACCESS_RECORD.md','00_ROLD_COMMANDS_TidyUp_BootUp.md','00_TOOLS_INDEX.md','00_LOOSE_ENDS_2026-07-16.md','00_NEXT_SESSION_HANDOFF_2026-07-15.md'); foreach($f in $p){ $a='V:\Research4\Ai\'+$f; $b='V:\Research4\Ai\PhD2_DATA_ARCHIVE\00_WORKING\'+$f; $sa=(Get-Item $a -ErrorAction SilentlyContinue).Length; $sb=(Get-Item $b -ErrorAction SilentlyContinue).Length; $ha=(Get-FileHash $a -Algorithm MD5 -ErrorAction SilentlyContinue).Hash; $hb=(Get-FileHash $b -Algorithm MD5 -ErrorAction SilentlyContinue).Hash; $v = if($ha -eq $hb){'MATCH'}else{'*** MISMATCH ***'}; '{0,-45} live={1,-8} mirror={2,-8} {3}' -f $f,$sa,$sb,$v }" >> "%OUT%" 2>&1
echo. >> "%OUT%"

echo --- 5. NEGATIVE CONTROL for check 4 ^(must print MISMATCH, else the check is blind^) --- >> "%OUT%"
powershell -NoProfile -Command "$a='V:\Research4\Ai\00_ROLD_COMMANDS_TidyUp_BootUp.md'; $b='V:\Research4\Ai\00_TOOLS_INDEX.md'; $ha=(Get-FileHash $a -Algorithm MD5).Hash; $hb=(Get-FileHash $b -Algorithm MD5).Hash; $v = if($ha -eq $hb){'MATCH (BAD - check is blind!)'}else{'MISMATCH (correct - check can detect difference)'}; 'ROLD vs TOOLS_INDEX -> ' + $v" >> "%OUT%" 2>&1
echo. >> "%OUT%"

echo ==== DONE ==== >> "%OUT%"
