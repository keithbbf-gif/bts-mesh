@echo off
set OUT=V:\Research4\Ai\BTS_MESH\_step4_check.txt
echo ==== STEP 4 — EXTERNAL REFS, CHECKED PROPERLY %DATE% %TIME% ==== > "%OUT%"
echo. >> "%OUT%"
echo  MY BUG, THREE TIMES TODAY: PowerShell -SimpleMatch with 'V:\\Research4' searches for the >> "%OUT%"
echo  LITERAL two-backslash string and finds nothing. It reported "0 refs" for files that had 2 and 3. >> "%OUT%"
echo  A search that cannot match is not a search. Use [regex]::Escape + -Pattern, or grep both forms. >> "%OUT%"
echo. >> "%OUT%"

echo --- 4a-FIXED. Who ACTUALLY points at V:\Research4 from outside the tree? --- >> "%OUT%"
powershell -NoProfile -Command ^
 "$rx=[regex]::Escape('V:\Research4');" ^
 "$t=@('C:\Users\Papa\OneDrive\Desktop\KDash.vbs','C:\Users\Papa\OneDrive\Desktop\JDash.vbs','D:\R2Cloner\Publish-to-R2_KEYED.bat','D:\R2Cloner\r2.bat');" ^
 "foreach($p in $t){ if(Test-Path $p){ $c=Get-Content $p -Raw -EA SilentlyContinue; $n=([regex]::Matches($c,$rx)).Count; '{0,-46} {1,3} refs' -f (Split-Path $p -Leaf),$n } else { '{0,-46} not present' -f (Split-Path $p -Leaf) } }" >> "%OUT%" 2>&1
echo. >> "%OUT%"

echo --- 4b-FIXED. SCHEDULED TASKS --- >> "%OUT%"
powershell -NoProfile -Command ^
 "$rx=[regex]::Escape('V:\Research4');" ^
 "$f=Get-ChildItem 'C:\Users\Papa\Claude\Scheduled' -Recurse -File -EA SilentlyContinue;" ^
 "if(-not $f){ '  no scheduled-task files found at C:\Users\Papa\Claude\Scheduled' }" ^
 "foreach($x in $f){ $c=Get-Content $x.FullName -Raw -EA SilentlyContinue; $n=([regex]::Matches($c,$rx)).Count; '{0,-52} {1,3} refs' -f ($x.FullName -replace [regex]::Escape('C:\Users\Papa\Claude\Scheduled\'),''),$n }" >> "%OUT%" 2>&1
echo. >> "%OUT%"

echo --- 4c. Are the staged .NEW files present and clean? --- >> "%OUT%"
powershell -NoProfile -Command ^
 "$rx=[regex]::Escape('V:\Research4');" ^
 "foreach($p in @('C:\Users\Papa\OneDrive\Desktop\KDash.vbs.NEW','D:\R2Cloner\Publish-to-R2_KEYED.bat.NEW')){" ^
 "  if(Test-Path $p){ $c=Get-Content $p -Raw; $n=([regex]::Matches($c,$rx)).Count; $v=([regex]::Matches($c,[regex]::Escape('V:\Research4'))).Count;" ^
 "    '  {0,-48} old-refs {1}  new-refs {2}  {3}' -f (Split-Path $p -Leaf),$n,$v,$(if($n -eq 0 -and $v -gt 0){'READY'}else{'*** CHECK ***'}) }" ^
 "  else { '  {0} MISSING' -f $p } }" >> "%OUT%" 2>&1
echo. >> "%OUT%"

echo --- 4d. bts_paths: the last "live ref" is a COMMENT, not a path. Show it. --- >> "%OUT%"
powershell -NoProfile -Command "Select-String -Path 'V:\Research4\Ai\BTS_MESH\bts_paths.py' -Pattern ([regex]::Escape('V:\Research4')) | ForEach-Object { '  line {0}: {1}' -f $_.LineNumber,$_.Line.Trim() }" >> "%OUT%" 2>&1
echo. >> "%OUT%"

echo --- 4e. Does the NEW tree's ROLD/CLAUDE point at V:? --- >> "%OUT%"
powershell -NoProfile -Command ^
 "foreach($p in @('V:\Research4\CLAUDE.md','V:\Research4\Ai\00_ROLD_COMMANDS_TidyUp_BootUp.md')){" ^
 "  $c=Get-Content $p -Raw; $old=([regex]::Matches($c,[regex]::Escape('V:\Research4'))).Count; $new=([regex]::Matches($c,[regex]::Escape('V:\Research4'))).Count;" ^
 "  '  {0,-46} D:refs {1}   V:refs {2}' -f (Split-Path $p -Leaf),$old,$new }" >> "%OUT%" 2>&1
echo. >> "%OUT%"
echo ==== DONE ==== >> "%OUT%"
type "%OUT%"
