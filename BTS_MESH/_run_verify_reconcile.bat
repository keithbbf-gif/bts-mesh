@echo off
cd /d "V:\Research4\Ai\BTS_MESH"
python _verify_and_reconcile.py > verify_reconcile.log 2>&1
echo EXIT=%errorlevel% >> verify_reconcile.log
