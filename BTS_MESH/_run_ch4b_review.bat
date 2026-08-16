@echo off
cd /d "V:\Research4\Ai\BTS_MESH"
python _ch4b_review.py > ch4b_review.log 2>&1
echo EXIT=%errorlevel% >> ch4b_review.log
