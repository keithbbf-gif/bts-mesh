@echo off
cd /d V:\Research4\Ai\BTS_MESH
echo ============================================================
echo  CREDIT PROBE - deliberate spend on the Joanna $300 trial
echo  Target ~$0.02 of gemini-2.5-pro on Agent Platform = ~1 call.
echo.
echo  Keith, 2026-07-16: "I killed that test when I say you want
echo  to spend a $1 to test. Spend 2 cents, not a dollar."
echo  He is right. Billing-^>Reports shows CENTS, so $0.02 clears
echo  rounding exactly as well as $1.00. The other 98c bought
echo  nothing but a 25-minute wait. ASK BEFORE PICKING A NUMBER.
echo.
echo  Risk: none - un-activated free trial, no card behind it.
echo  Purpose: spend ENOUGH TO CLEAR ROUNDING so Billing-^>Reports
echo           can finally say whether the $300 pays for Vertex.
echo ============================================================
python bts_creditprobe.py --usd 0.02
echo.
echo ---- exit=%ERRORLEVEL% ----
pause
