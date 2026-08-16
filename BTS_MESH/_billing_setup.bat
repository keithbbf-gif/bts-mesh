@echo off
set OUT=V:\Research4\Ai\BTS_MESH\_billing_setup.txt
set SRC=C:\Users\Papa\Downloads\client_secret_614387154970-gq5u2qbcb1it0uojkepbomhd3t08dapl.apps.googleusercontent.com.json
set DST=V:\Research4\.secrets\gcp_billing_oauth.json
echo ==== BILLING OAUTH SETUP %DATE% %TIME% ==== > "%OUT%"
echo. >> "%OUT%"
echo --- 1. move client JSON into .secrets ^(OUTSIDE the published Ai\ tree, by location^) --- >> "%OUT%"
copy /Y "%SRC%" "%DST%" >> "%OUT%" 2>&1
powershell -NoProfile -Command "$a='%SRC%'; $b='%DST%'; $ha=(Get-FileHash $a -Algorithm MD5 -EA SilentlyContinue).Hash; $hb=(Get-FileHash $b -Algorithm MD5 -EA SilentlyContinue).Hash; if($ha -eq $hb){'   MD5 MATCH - copy is intact'}else{'   *** MISMATCH / MISSING ***'}" >> "%OUT%" 2>&1
echo. >> "%OUT%"
echo --- 2. python deps present? --- >> "%OUT%"
python -c "import google_auth_oauthlib; print('   google_auth_oauthlib OK', google_auth_oauthlib.__version__)" >> "%OUT%" 2>&1
python -c "import google.auth, google.auth.transport.requests; print('   google-auth OK')" >> "%OUT%" 2>&1
python -c "import requests; print('   requests OK', requests.__version__)" >> "%OUT%" 2>&1
echo. >> "%OUT%"
echo ==== DONE ==== >> "%OUT%"
