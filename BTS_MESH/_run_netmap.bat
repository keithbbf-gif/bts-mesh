@echo off
cd /d V:\Research4\Ai\BTS_MESH
set OUT=V:\Research4\Ai\BTS_MESH\_run_netmap.txt
echo ==== NETMAP %DATE% %TIME% ==== > "%OUT%"
echo  Run on the HOST: the Linux sandbox serves a TRUNCATED copy of this file through the FUSE >> "%OUT%"
echo  mount (compile there dies at line 144 mid-statement; host Read shows it intact). FUSE hit #10. >> "%OUT%"
echo. >> "%OUT%"
python _netmap.py >> "%OUT%" 2>&1
echo    exit=%ERRORLEVEL% >> "%OUT%"
powershell -NoProfile -Command "$p='V:\Research4\Ai\BTS_MESH\KMESH_NETWORK_MAP_2026-07-16.png'; if(Test-Path $p){ $f=Get-Item $p; '   PNG {0} bytes  {1}' -f $f.Length,$f.LastWriteTime } else { '   PNG MISSING' }" >> "%OUT%" 2>&1
type "%OUT%"
