@echo off
cd /d V:\Research4\Ai\BTS_MESH
set OUT=V:\Research4\Ai\BTS_MESH\_seed_calibration.txt
echo ==== SEED CALIBRATION %DATE% %TIME% ==== > "%OUT%"
echo. >> "%OUT%"
echo --- vertex: our ledger read $0.037731 for the SAME period Google's console counted $0.09 --- >> "%OUT%"
echo     (console: "Free trial status: $299.91 credit and 89 days remaining"  =^> 300.00 - 299.91 = 0.09) >> "%OUT%"
python bts_calibrate.py vertex --actual 0.09 --est 0.037731 --note "console banner 2026-07-16: $299.91 of $300, 89d left. --est passed explicitly because vertex_usage.json spend was already SET to Googles 0.09; reading the ledger would compare 0.09 to 0.09 and record a false 1.00x." >> "%OUT%" 2>&1
echo. >> "%OUT%"
echo ==== DONE ==== >> "%OUT%"
type "%OUT%"
