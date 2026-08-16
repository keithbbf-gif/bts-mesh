@echo off
REM ===================================================================================
REM  _run_verify_joanna.bat - prove both Gemini rails on the JOANNA account. 2026-07-15.
REM  Double-click me. Nothing here spends more than ~$0.001.
REM ===================================================================================
setlocal
cd /d "%~dp0"

echo.
echo  ============================================================================
echo   JOANNA RAIL VERIFY
echo   billing 010E47-824B53-7202F5 ^| project project-5a33f910-1251-4d6a-bf9
echo  ============================================================================
echo.
echo   Checklist:  JOANNA_RAIL_SETUP_2026-07-15.md
echo   THE ONE RULE: do NOT click "Activate" / "Upgrade to paid".
echo                 Non-billable is the whole safety property - worst case is an
echo                 ERROR, not a charge. Activating also kills the free daily quota
echo                 (Paid account =^> Tier 1 =^> prepay required). Same failure as the
echo                 account you just deleted.
echo.

where py >nul 2>&1
if %errorlevel%==0 (
    py -3 "_verify_joanna_rails.py"
) else (
    where python >nul 2>&1
    if %errorlevel%==0 (
        python "_verify_joanna_rails.py"
    ) else (
        echo   *** No Python on PATH. Tried "py -3" and "python". ***
        echo   Run the script by hand: _verify_joanna_rails.py
    )
)

echo.
echo  ============================================================================
echo   IF BOTH PASSED, ONE THING IS LEFT AND CODE CANNOT DO IT:
echo   Nothing above proves the $300 is PAYING for Vertex.
echo.
echo   *** WAIT ~24 HOURS BEFORE READING THE METER. ***
echo   Google: "Typically, your costs are available within a day, but can
echo   sometimes take more than 24 hours." An empty report right now means
echo   NOTHING. Do not conclude from it.
echo.
echo     https://console.cloud.google.com/billing/010E47-824B53-7202F5/reports
echo     Group by SKU, range = today, find the Agent Platform / Gemini row.
echo.
echo   HOW TO READ IT (easy to get backwards): "Usage cost" is ALWAYS populated,
echo   it is the on-demand rate. It is NOT the signal. The credit shows up as a
echo   SEPARATE OFFSETTING LINE. Google's own example:
echo.
echo       SKU                      Usage cost  Other savings  Subtotal
echo       N1 Predefined Instance   $33.75      -$33.75        $0.00
echo.
echo     "Other savings" NEGATIVE + Subtotal $0.00  -^> CREDIT PAID IT. Burn it.
echo     "Other savings" $0.00 + Subtotal ^> $0      -^> credit NOT covering Vertex.
echo.
echo   *** DO NOT USE THE CLOUD HUB "Optimization" PAGE. *** It shows GROSS cost,
echo   "before any ... credits are applied" - credits are INVISIBLE there. It will
echo   look exactly like the credit failed either way. FALSE NEGATIVE GUARANTEED.
echo   Billing -^> Reports, nothing else.
echo.
echo   Then fix CREDIT_EXPIRES in bts_vertex.py from the console's REAL date.
echo   It is currently a COMPUTED guess (start + 90d). Read it, do not compute it.
echo  ============================================================================
echo.
pause
endlocal
