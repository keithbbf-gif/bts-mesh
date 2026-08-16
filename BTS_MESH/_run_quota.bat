@echo off
cd /d "V:\Research4\Ai\BTS_MESH"
python bts_quota.py > quota.log 2>&1
echo EXIT=%errorlevel% >> quota.log
