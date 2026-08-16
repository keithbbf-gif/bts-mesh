@echo off
REM ============================================================================
REM  MIGRATION STEP 1 — COPY  V:\Research4  ->  V:\Research4
REM
REM  SAFE AND ADDITIVE. Nothing points at V: yet; D: is untouched and keeps working.
REM  The irreversible step (Keith renaming V:\Research4 -> D:\Research3) is LAST, not here.
REM
REM  HOST-SIDE ON PURPOSE: the FUSE mount CORRUPTS (10 hits — faked JSON errors on healthy
REM  files, served a script truncated mid-line). Copying 87,014 files through /mnt would
REM  carry that corruption into the new tree SILENTLY. robocopy on Windows, or not at all.
REM
REM  /E        all subdirs incl. empty        /COPY:DAT  data+attrs+timestamps
REM  /R:1 /W:1 do not hang on a locked file   /XF .fuse_hidden*  FUSE artifacts, not ours
REM  NO /MIR — mirror can DELETE. This must only ever add.
REM ============================================================================
set SRC=V:\Research4
set DST=V:\Research4
set OUT=V:\Research4\Ai\BTS_MESH\_migrate_step1.txt
set LOG=V:\Research4\Ai\BTS_MESH\_migrate_robocopy.log

echo ==== MIGRATE STEP 1: COPY %DATE% %TIME% ==== > "%OUT%"
echo   SRC %SRC%  ->  DST %DST% >> "%OUT%"
echo   expect ~31.58 GB / 87,014 files. Source is a USB HDD @92.7 MB/s = the ceiling (~6+ min). >> "%OUT%"
echo. >> "%OUT%"

echo --- BEFORE: source truth --- >> "%OUT%"
powershell -NoProfile -Command "$m=Get-ChildItem 'V:\Research4' -Recurse -File -Force -EA SilentlyContinue | Measure-Object -Property Length -Sum; '  SRC files {0}  bytes {1}  ({2} GB)' -f $m.Count,$m.Sum,[math]::Round($m.Sum/1GB,2)" >> "%OUT%" 2>&1
powershell -NoProfile -Command "$v=Get-Volume -DriveLetter V; '  V: free before {0} GB' -f [math]::Round($v.SizeRemaining/1GB,1)" >> "%OUT%" 2>&1
echo. >> "%OUT%"

echo --- COPYING (this takes minutes; robocopy log: %LOG%) --- >> "%OUT%"
robocopy "%SRC%" "%DST%" /E /COPY:DAT /R:1 /W:1 /XF .fuse_hidden* /NFL /NDL /NP /LOG:"%LOG%"
set RC=%ERRORLEVEL%
echo   robocopy exit=%RC%  ^(0=nothing new, 1=files copied, ^<8 = OK, ^>=8 = FAILURE^) >> "%OUT%"
echo. >> "%OUT%"

echo --- AFTER: did it all land? --- >> "%OUT%"
powershell -NoProfile -Command ^
 "$s=Get-ChildItem 'V:\Research4' -Recurse -File -Force -EA SilentlyContinue | Measure-Object -Property Length -Sum;" ^
 "$d=Get-ChildItem 'V:\Research4' -Recurse -File -Force -EA SilentlyContinue | Measure-Object -Property Length -Sum;" ^
 "'  SRC  {0,7} files  {1,14} bytes' -f $s.Count,$s.Sum;" ^
 "'  DST  {0,7} files  {1,14} bytes' -f $d.Count,$d.Sum;" ^
 "$fd=$s.Count-$d.Count; $bd=$s.Sum-$d.Sum;" ^
 "'  diff {0,7} files  {1,14} bytes' -f $fd,$bd;" ^
 "if($fd -eq 0 -and $bd -eq 0){'  *** COUNT+BYTES MATCH ***'}else{'  *** MISMATCH — investigate before ANY further step ***'}" >> "%OUT%" 2>&1
echo. >> "%OUT%"

echo --- SAMPLE MD5 (count+bytes can match while content is corrupt) --- >> "%OUT%"
powershell -NoProfile -Command ^
 "$rel=@('CLAUDE.md','Ai\00_ROLD_COMMANDS_TidyUp_BootUp.md','Ai\BTS_MESH\bts_vertex.py','Ai\BTS_MESH\jack_command.html','Ai\BTS_MESH\TOOLS_REGISTRY.json','.secrets\vertex_key.txt');" ^
 "$bad=0; foreach($r in $rel){ $a='V:\Research4\'+$r; $b='V:\Research4\'+$r;" ^
 "  if(-not (Test-Path $a)){ '  {0,-44} SRC MISSING' -f $r; continue }" ^
 "  if(-not (Test-Path $b)){ $bad++; '  {0,-44} *** DST MISSING ***' -f $r; continue }" ^
 "  $ha=(Get-FileHash $a -Algorithm MD5).Hash; $hb=(Get-FileHash $b -Algorithm MD5).Hash;" ^
 "  if($ha -eq $hb){ '  {0,-44} MATCH' -f $r } else { $bad++; '  {0,-44} *** CORRUPT ***' -f $r } };" ^
 "''; '  sample bad = ' + $bad" >> "%OUT%" 2>&1
echo. >> "%OUT%"

echo --- NEGATIVE CONTROL (the check must be able to FAIL) --- >> "%OUT%"
powershell -NoProfile -Command "$a='V:\Research4\CLAUDE.md'; $b='V:\Research4\Ai\00_MESH_CHARTER.md'; if(Test-Path $b){ $v = if((Get-FileHash $a -Algorithm MD5).Hash -eq (Get-FileHash $b -Algorithm MD5).Hash){'MATCH (BAD - blind!)'}else{'MISMATCH (correct - it can detect a difference)'}; '  CLAUDE.md vs CHARTER -> ' + $v }" >> "%OUT%" 2>&1
echo. >> "%OUT%"

echo --- .secrets kept its PROPERTY? (safe by LOCATION: sibling of Ai\, outside the published tree) --- >> "%OUT%"
powershell -NoProfile -Command "if(Test-Path 'V:\Research4\.secrets'){ '  V:\Research4\.secrets EXISTS and is OUTSIDE V:\Research4\Ai\  -> property preserved' } else { '  *** .secrets MISSING at destination ***' }" >> "%OUT%" 2>&1
echo. >> "%OUT%"
echo ==== DONE — NOTHING has been renamed or deleted. V:\Research4 is untouched. ==== >> "%OUT%"
type "%OUT%"
