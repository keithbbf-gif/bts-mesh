@echo off
cd /d V:\Research4\Ai\BTS_MESH
set OUT=V:\Research4\Ai\BTS_MESH\_calib_vertex2.txt
echo ==== VERTEX RECALIBRATION #2 %DATE% %TIME% ==== > "%OUT%"
echo   console banner: "$299.89 credit and 89 days remaining"  =^>  300.00 - 299.89 = $0.11 ACTUAL >> "%OUT%"
echo   our RAW ledger (vertex_usage.json spend) = 0.07868095 >> "%OUT%"
echo   previous factor was 2.39x (thinking tokens were NOT counted at all) >> "%OUT%"
echo. >> "%OUT%"
python bts_calibrate.py vertex --actual 0.11 --est 0.07868095 --note "console banner 2026-07-16 ~11:20: $299.89 of $300 = $0.11 spent. SECOND reconciliation. The ledger now spans BOTH pre-fix calls (thoughtsTokenCount ignored) and post-fix calls (thinking counted + thinkingBudget capped), so this factor is a BLEND and should keep falling toward ~1.0 as post-fix calls dominate. ALSO FOUND: AI/Agent Studio Settings->Usage shows INPUT+OUTPUT TOKEN COUNT PER DAY PER MODEL (last 7d, 19 models) - token counts, not dollars, but it is real per-model compute visibility." >> "%OUT%" 2>&1
echo. >> "%OUT%"
echo ==== DONE ==== >> "%OUT%"
type "%OUT%"
