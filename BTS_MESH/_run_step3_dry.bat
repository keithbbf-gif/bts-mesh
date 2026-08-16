@echo off
cd /d V:\Research4\Ai\BTS_MESH
set OUT=V:\Research4\Ai\BTS_MESH\_migrate_step3_dry.txt
echo ==== STEP 3 DRY RUN %DATE% %TIME% ==== > "%OUT%"
python _migrate_step3_paths.py >> "%OUT%" 2>&1
echo. >> "%OUT%"
echo --- bts_paths resolver self-test (host) --- >> "%OUT%"
python bts_paths.py >> "%OUT%" 2>&1
type "%OUT%"
