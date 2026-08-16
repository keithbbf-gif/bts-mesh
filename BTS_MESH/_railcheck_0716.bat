@echo off
set OUT=V:\Research4\Ai\BTS_MESH\_railcheck_0716.txt
cd /d V:\Research4\Ai\BTS_MESH
echo ==== RAIL CHECK %DATE% %TIME% ==== > "%OUT%"
echo (rails run NATIVELY on Windows - the Linux sandbox has no drive letters and cannot do this) >> "%OUT%"
echo. >> "%OUT%"

echo --- 0. KEY IDENTITY: is gemini_key.txt the SAME key as vertex_key.txt? (md5 of the key, never the key) --- >> "%OUT%"
powershell -NoProfile -Command "$g='V:\Research4\.secrets\gemini_key.txt'; $v='V:\Research4\.secrets\vertex_key.txt'; $hg=(Get-FileHash $g -Algorithm MD5).Hash; $hv=(Get-FileHash $v -Algorithm MD5).Hash; 'gemini_key.txt md5 = ' + $hg; 'vertex_key.txt md5 = ' + $hv; if($hg -eq $hv){'*** SAME KEY - the two rails are ONE credential, not two ***'}else{'DIFFERENT keys - genuinely two credentials'}" >> "%OUT%" 2>&1
echo. >> "%OUT%"

echo --- 1. GEM rail (bts_gem: AI Studio free tier, expected 429 if billing-linked) --- >> "%OUT%"
python -c "import sys; sys.path.insert(0,r'V:\Research4\Ai\BTS_MESH'); from bts_gem import ask; r=ask('Reply with exactly one word: OK'); print(repr(r)[:400])" >> "%OUT%" 2>&1
echo    exit=%ERRORLEVEL% >> "%OUT%"
echo. >> "%OUT%"

echo --- 2. VERTEX rail (bts_vertex: the $300 / Joanna account) --- >> "%OUT%"
python -c "import sys; sys.path.insert(0,r'V:\Research4\Ai\BTS_MESH'); from bts_vertex import ask; r=ask('Reply with exactly one word: OK'); print(repr(r)[:400])" >> "%OUT%" 2>&1
echo    exit=%ERRORLEVEL% >> "%OUT%"
echo. >> "%OUT%"

echo --- 3. SGH rail (bts_sgh: PAID xAI - ungrounded, ~$0.001, governor must REFUSE search=True) --- >> "%OUT%"
python -c "import sys; sys.path.insert(0,r'V:\Research4\Ai\BTS_MESH'); from bts_sgh import ask; r=ask('Reply with exactly one word: OK'); print(repr(r)[:400])" >> "%OUT%" 2>&1
echo    exit=%ERRORLEVEL% >> "%OUT%"
echo. >> "%OUT%"

echo --- 3b. SGH GOVERNOR NEGATIVE CONTROL: search=True MUST be refused --- >> "%OUT%"
python -c "import sys; sys.path.insert(0,r'V:\Research4\Ai\BTS_MESH'); from bts_sgh import ask; ask('test',search=True); print('*** GOVERNOR FAILED - the paid search rail was NOT refused ***')" >> "%OUT%" 2>&1
echo    ^(a REFUSED/raise above = governor WORKING^) >> "%OUT%"
echo. >> "%OUT%"

echo --- 4. GDX rail (Drive) --- >> "%OUT%"
python -c "import sys; sys.path.insert(0,r'V:\Research4\Ai\BTS_MESH'); import bts_gdx; print('bts_gdx imported OK')" >> "%OUT%" 2>&1
echo    exit=%ERRORLEVEL% >> "%OUT%"
echo. >> "%OUT%"

echo --- 5. GDX OAuth FUSE: which project does client_secrets.json point at? (no secrets printed) --- >> "%OUT%"
powershell -NoProfile -Command "$p='V:\Research4\Ai\client_secrets.json'; if(Test-Path $p){ $j=Get-Content $p -Raw | ConvertFrom-Json; $c=$j.installed; if(-not $c){$c=$j.web}; 'project_id = ' + $c.project_id; 'client_id tail = ...' + $c.client_id.Substring([Math]::Max(0,$c.client_id.Length-18)) } else { 'client_secrets.json ABSENT' }" >> "%OUT%" 2>&1
echo. >> "%OUT%"

echo --- 6. DASHBOARD: is bts_serve.py listening on 8765? --- >> "%OUT%"
powershell -NoProfile -Command "$r = Test-NetConnection -ComputerName 127.0.0.1 -Port 8765 -InformationLevel Quiet -WarningAction SilentlyContinue; 'port 8765 open = ' + $r" >> "%OUT%" 2>&1
powershell -NoProfile -Command "try{ $c=Invoke-WebRequest -Uri 'http://127.0.0.1:8765/dash.json' -UseBasicParsing -TimeoutSec 5; 'dash.json served: HTTP ' + $c.StatusCode + '  bytes=' + $c.Content.Length }catch{ 'dash.json NOT served: ' + $_.Exception.Message }" >> "%OUT%" 2>&1
echo. >> "%OUT%"

echo --- 7. DASH FILES: names + freshness (the JDash/KDash question) --- >> "%OUT%"
powershell -NoProfile -Command "Get-ChildItem 'V:\Research4\Ai\BTS_MESH\*.html','V:\Research4\Ai\BTS_MESH\*.vbs','V:\Research4\Ai\BTS_MESH\bts_serve.py','V:\Research4\Ai\BTS_MESH\dash.json' -ErrorAction SilentlyContinue | Select-Object Name,Length,LastWriteTime | Format-Table -AutoSize | Out-String -Width 200" >> "%OUT%" 2>&1
powershell -NoProfile -Command "Get-ChildItem 'C:\Users\Papa\OneDrive\Desktop\*.vbs' -ErrorAction SilentlyContinue | Select-Object Name,Length,LastWriteTime | Format-Table -AutoSize | Out-String -Width 200" >> "%OUT%" 2>&1
echo. >> "%OUT%"

echo --- 8. how many refs would a jack_command -^> kdash rename break? --- >> "%OUT%"
powershell -NoProfile -Command "$h=(Select-String -Path 'V:\Research4\Ai\BTS_MESH\*.*','C:\Users\Papa\OneDrive\Desktop\*.vbs' -Pattern 'jack_command' -SimpleMatch -ErrorAction SilentlyContinue); 'jack_command refs = ' + $h.Count; $h | Group-Object Filename | ForEach-Object { '   ' + $_.Name + '  x' + $_.Count }" >> "%OUT%" 2>&1
powershell -NoProfile -Command "$h=(Select-String -Path 'V:\Research4\Ai\BTS_MESH\*.*' -Pattern 'JDash|Jack''s Mesh' -ErrorAction SilentlyContinue); 'JDash/Jacks-Mesh refs = ' + $h.Count" >> "%OUT%" 2>&1
echo. >> "%OUT%"
echo ==== DONE ==== >> "%OUT%"
