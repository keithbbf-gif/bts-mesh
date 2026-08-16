@echo off
cd /d "V:\Research4\Ai\BTS_MESH"
python -m pip install pillow numpy matplotlib --quiet
python bts_figdig.py > figdig_selftest.log 2>&1
echo EXIT=%errorlevel% >> figdig_selftest.log
