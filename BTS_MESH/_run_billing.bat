@echo off
cd /d V:\Research4\Ai\BTS_MESH
echo ============================================================
echo  BTS BILLING METER - reads GOOGLE'S figure, not our estimate
echo.
echo  A browser will open ONCE for consent (sign in as Joanna,
echo  approve READ-ONLY billing). After that it runs silently.
echo ============================================================
echo.
echo --- installing google-auth-oauthlib (the only missing dep) ---
python -m pip install --quiet --disable-pip-version-check google-auth-oauthlib
echo    pip-exit=%ERRORLEVEL%
echo.
python bts_billing.py
echo.
echo ---- exit=%ERRORLEVEL% ----
pause
