@echo off
cd /d "V:\Research4\Ai\BTS_MESH"
python bts_review.py "V:\Research4\Ai\PhD2_DATA_ARCHIVE\00_WORKING\CH4_ARCHITECTURE_v2_2026-07-13.md" "V:\Research4\Ai\PhD2_DATA_ARCHIVE\00_WORKING\CH4_BEAMLINE_RESTRUCTURE_2026-07-13.md" "V:\Research4\Ai\PhD2_DATA_ARCHIVE\00_WORKING\SOP_SPECTRUM_VALIDATION_2026-07-13.md" > ch4_review.log 2>&1
echo EXIT=%errorlevel% >> ch4_review.log
