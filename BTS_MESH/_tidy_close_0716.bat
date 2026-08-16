@echo off
set OUT=V:\Research4\Ai\BTS_MESH\_tidy_close_0716.txt
set W=V:\Research4\Ai\PhD2_DATA_ARCHIVE\00_WORKING
echo ==== SESSION CLOSE %DATE% %TIME% ==== > "%OUT%"
echo. >> "%OUT%"

echo --- 1. bts_gem still compiles after the vision-path fix? --- >> "%OUT%"
cd /d V:\Research4\Ai\BTS_MESH
python -c "import py_compile;py_compile.compile(r'V:\Research4\Ai\BTS_MESH\bts_gem.py',doraise=True);print('   bts_gem.py OK')" >> "%OUT%" 2>&1
python -c "import sys;sys.path.insert(0,r'V:\Research4\Ai\BTS_MESH');import bts_gem;print('   VERTEX_FAILOVER_MODEL =',bts_gem.VERTEX_FAILOVER_MODEL)" >> "%OUT%" 2>&1
echo. >> "%OUT%"

echo --- 2. MIRROR today's deliverables -^> 00_WORKING --- >> "%OUT%"
for %%F in (
  00_MESH_CHARTER.md
  00_MIGRATION_RESEARCH4_2026-07-16.md
  00_HARVEST_2026-07-16.md
  00_TASK_COMPLETE_KMESH.md
  00_ROLD_COMMANDS_TidyUp_BootUp.md
) do copy /Y "V:\Research4\Ai\%%F" "%W%\%%F" >> "%OUT%" 2>&1
copy /Y "V:\Research4\Ai\BTS_MESH\TB1_MAXDRIVE_2026-07-16.md" "%W%\TB1_MAXDRIVE_2026-07-16.md" >> "%OUT%" 2>&1
copy /Y "V:\Research4\Ai\BTS_MESH\KMESH_NETWORK_MAP_2026-07-16.png" "%W%\KMESH_NETWORK_MAP_2026-07-16.png" >> "%OUT%" 2>&1
echo. >> "%OUT%"

echo --- 3. VERIFY mirror by MD5 (a publish is not a sync) --- >> "%OUT%"
powershell -NoProfile -Command "$p=@('00_MESH_CHARTER.md','00_MIGRATION_RESEARCH4_2026-07-16.md','00_HARVEST_2026-07-16.md','00_TASK_COMPLETE_KMESH.md'); $bad=0; foreach($f in $p){ $a='V:\Research4\Ai\'+$f; $b='V:\Research4\Ai\PhD2_DATA_ARCHIVE\00_WORKING\'+$f; $ha=(Get-FileHash $a -Algorithm MD5 -EA SilentlyContinue).Hash; $hb=(Get-FileHash $b -Algorithm MD5 -EA SilentlyContinue).Hash; if($ha -eq $hb){'  {0,-46} MATCH' -f $f}else{$bad++;'  {0,-46} *** MISMATCH ***' -f $f} }; ''; '  BAD = '+$bad" >> "%OUT%" 2>&1
echo. >> "%OUT%"

echo --- 4. NEGATIVE CONTROL --- >> "%OUT%"
powershell -NoProfile -Command "$v = if((Get-FileHash 'V:\Research4\Ai\00_MESH_CHARTER.md' -Algorithm MD5).Hash -eq (Get-FileHash 'V:\Research4\Ai\00_HARVEST_2026-07-16.md' -Algorithm MD5).Hash){'MATCH (BAD - blind!)'}else{'MISMATCH (correct)'}; '  CHARTER vs HARVEST -> '+$v" >> "%OUT%" 2>&1
echo. >> "%OUT%"

echo --- 5. re-sync the delta into V:\Research4 + re-rewrite its paths --- >> "%OUT%"
robocopy "V:\Research4\Ai" "V:\Research4\Ai" /E /COPY:DAT /R:1 /W:1 /XF .fuse_hidden* /NFL /NDL /NP /NJH /NJS >> "%OUT%" 2>&1
python _migrate_step3_paths.py --go >> "%OUT%" 2>&1
echo. >> "%OUT%"

echo ==== MIRROR DONE — launching R2 publish ==== >> "%OUT%"
type "%OUT%"
start "" "D:\R2Cloner\Publish-to-R2_KEYED.bat"
