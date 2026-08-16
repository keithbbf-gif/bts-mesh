@echo off
cd /d "V:\Research4\Ai\BTS_MESH"
python bts_chanbench.py > chanbench.log 2>&1
echo EXIT=%errorlevel% >> chanbench.log
