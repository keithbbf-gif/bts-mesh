@echo off
cd /d V:\Research4\Ai\BTS_MESH
set OUT=V:\Research4\Ai\BTS_MESH\_run_meters.txt
python bts_meters.py > "%OUT%" 2>&1
type "%OUT%"
