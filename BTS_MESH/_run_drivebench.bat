@echo off
cd /d "V:\Research4\Ai\BTS_MESH"
python bts_drivebench.py > drivebench.log 2>&1
echo EXIT=%errorlevel% >> drivebench.log
