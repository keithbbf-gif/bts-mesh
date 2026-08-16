@echo off
set OUT=V:\Research4\Ai\BTS_MESH\_tidy_0716b.txt
set W=V:\Research4\Ai\PhD2_DATA_ARCHIVE\00_WORKING
echo ==== FINAL MIRROR %DATE% %TIME% ==== > "%OUT%"
echo. >> "%OUT%"
echo --- mirror living docs + this session's outputs -^> 00_WORKING --- >> "%OUT%"
copy /Y "V:\Research4\Ai\00_FOLDER_ACCESS_RECORD.md"            "%W%\00_FOLDER_ACCESS_RECORD.md" >> "%OUT%" 2>&1
copy /Y "V:\Research4\Ai\00_ROLD_COMMANDS_TidyUp_BootUp.md"     "%W%\00_ROLD_COMMANDS_TidyUp_BootUp.md" >> "%OUT%" 2>&1
copy /Y "V:\Research4\Ai\00_TOOLS_INDEX.md"                     "%W%\00_TOOLS_INDEX.md" >> "%OUT%" 2>&1
copy /Y "V:\Research4\Ai\00_LOOSE_ENDS_2026-07-16.md"           "%W%\00_LOOSE_ENDS_2026-07-16.md" >> "%OUT%" 2>&1
copy /Y "V:\Research4\Ai\00_NEXT_SESSION_HANDOFF_2026-07-15.md" "%W%\00_NEXT_SESSION_HANDOFF_2026-07-15.md" >> "%OUT%" 2>&1
copy /Y "V:\Research4\Ai\00_SESSION_WRAPUP_2026-07-16.md"       "%W%\00_SESSION_WRAPUP_2026-07-16.md" >> "%OUT%" 2>&1
echo. >> "%OUT%"
echo --- VERIFY live vs mirror by MD5 --- >> "%OUT%"
powershell -NoProfile -Command "$p=@('00_FOLDER_ACCESS_RECORD.md','00_ROLD_COMMANDS_TidyUp_BootUp.md','00_TOOLS_INDEX.md','00_LOOSE_ENDS_2026-07-16.md','00_NEXT_SESSION_HANDOFF_2026-07-15.md','00_SESSION_WRAPUP_2026-07-16.md'); $bad=0; foreach($f in $p){ $a='V:\Research4\Ai\'+$f; $b='V:\Research4\Ai\PhD2_DATA_ARCHIVE\00_WORKING\'+$f; $ha=(Get-FileHash $a -Algorithm MD5 -ErrorAction SilentlyContinue).Hash; $hb=(Get-FileHash $b -Algorithm MD5 -ErrorAction SilentlyContinue).Hash; if($ha -eq $hb){ '{0,-45} MATCH' -f $f } else { $bad++; '{0,-45} *** MISMATCH ***' -f $f } }; ''; 'BAD = ' + $bad" >> "%OUT%" 2>&1
echo. >> "%OUT%"
echo ==== MIRROR DONE - launching R2 publish ==== >> "%OUT%"
start "" "D:\R2Cloner\Publish-to-R2_KEYED.bat"
