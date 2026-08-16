@echo off
cd /d V:\Research4\Ai\BTS_MESH
set OUT=V:\Research4\Ai\BTS_MESH\_calib_sgh.txt
echo ==== SGH RECONCILIATION %DATE% %TIME% ==== > "%OUT%"
echo   console.x.ai/team/0a13aa38-96c2-4036-a3be-0ab7e234fe61/settings/billing >> "%OUT%"
echo   balance $6.67 of $10.00 purchased (12 Jul, Paid) =^> ACTUAL SPEND $3.33 >> "%OUT%"
echo   our ledger (sgh_spend.json WORK+POLL) = $3.3789 >> "%OUT%"
echo. >> "%OUT%"
python bts_calibrate.py sgh --actual 3.33 --est 3.3789 --note "console.x.ai settings/billing 2026-07-16: balance $6.67, $10.00 purchased 12 Jul (Paid) + $5.00 FAILED => spent 3.33. CONFIRMS xAI cost_in_usd_ticks is genuinely EXACT: we are 1.5%% HIGH (over-report = safe direction). Contrast vertex at 2.39x LOW. ALSO SEEN: auto top-up ON - charges $10 when balance <= $5; balance $6.67 = $1.67 from a card charge. The $10 stop is OUR code, not xAI's. Billing email dchamberss@gmail.com (3rd identity)." >> "%OUT%" 2>&1
echo. >> "%OUT%"
echo ==== DONE ==== >> "%OUT%"
type "%OUT%"
