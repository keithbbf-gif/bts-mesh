@echo off
set OUT=V:\Research4\Ai\BTS_MESH\_migrate_verify.txt
echo ==== STEP 3 VERIFY %DATE% %TIME% ==== > "%OUT%"
echo. >> "%OUT%"

echo --- 3a. DELTA SYNC: pick up everything created AFTER the first robocopy --- >> "%OUT%"
echo     (bts_paths.py and the migration scripts did not exist when the tree was copied) >> "%OUT%"
robocopy "V:\Research4\Ai\BTS_MESH" "V:\Research4\Ai\BTS_MESH" /E /COPY:DAT /R:1 /W:1 /XF .fuse_hidden* /NFL /NDL /NP /NJH /NJS >> "%OUT%" 2>&1
robocopy "V:\Research4\Ai" "V:\Research4\Ai" /COPY:DAT /R:1 /W:1 /XF .fuse_hidden* /NFL /NDL /NP /NJH /NJS >> "%OUT%" 2>&1
robocopy "V:\Research4" "V:\Research4" /COPY:DAT /R:1 /W:1 /XF .fuse_hidden* /NFL /NDL /NP /NJH /NJS >> "%OUT%" 2>&1
echo     delta sync done >> "%OUT%"
echo. >> "%OUT%"

echo --- 3b. RE-REWRITE any newly-synced file (the delta arrived with D: paths in it) --- >> "%OUT%"
cd /d V:\Research4\Ai\BTS_MESH
python _migrate_step3_paths.py --go >> "%OUT%" 2>&1
echo. >> "%OUT%"

echo --- 3c. VERIFY --- >> "%OUT%"
python _migrate_verify.py >> "%OUT%" 2>&1
echo. >> "%OUT%"

echo --- 3d. bts_paths, run FROM the new tree --- >> "%OUT%"
cd /d V:\Research4\Ai\BTS_MESH
python bts_paths.py >> "%OUT%" 2>&1
echo. >> "%OUT%"
echo ==== DONE ==== >> "%OUT%"
type "%OUT%"
