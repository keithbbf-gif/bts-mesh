@echo off
set OUT=V:\Research4\Ai\BTS_MESH\_diskbench.txt
echo ==== DISK BENCH %DATE% %TIME% ==== > "%OUT%"
echo  Sequential 1 GB write+read, then a 4K-random read pass. >> "%OUT%"
echo  WHY: for a PHOTO LIBRARY the RANDOM number is the one that matters (thumbnails/browsing), >> "%OUT%"
echo  not sequential. Gigabit = ~110 MB/s, so anything above that is not the bottleneck. >> "%OUT%"
echo. >> "%OUT%"

powershell -NoProfile -Command ^
  "$targets = @{ 'G: Sabrent USB3 8TB' = 'G:\_bench.tmp'; 'D: WD Passport USB' = 'D:\_bench.tmp'; 'V: ADATA NVMe' = 'V:\_bench.tmp'; 'C: SN850X NVMe' = 'C:\Users\Papa\_bench.tmp' };" ^
  "foreach($k in $targets.Keys){ $p=$targets[$k];" ^
  "  try{ $dir=Split-Path $p; if(-not (Test-Path $dir)){ '{0,-22} SKIP (no volume)' -f $k; continue }" ^
  "    $sz=512MB; $buf=New-Object byte[] (8MB); (New-Object Random).NextBytes($buf);" ^
  "    $sw=[Diagnostics.Stopwatch]::StartNew(); $fs=[IO.File]::Create($p);" ^
  "    for($i=0;$i -lt ($sz/8MB);$i++){ $fs.Write($buf,0,$buf.Length) }; $fs.Flush($true); $fs.Close(); $sw.Stop();" ^
  "    $w=[math]::Round(($sz/1MB)/$sw.Elapsed.TotalSeconds,1);" ^
  "    $sw=[Diagnostics.Stopwatch]::StartNew(); $fs=[IO.File]::OpenRead($p); $rb=New-Object byte[] (8MB);" ^
  "    while($fs.Read($rb,0,$rb.Length) -gt 0){}; $fs.Close(); $sw.Stop();" ^
  "    $r=[math]::Round(($sz/1MB)/$sw.Elapsed.TotalSeconds,1);" ^
  "    $fs=[IO.File]::OpenRead($p); $rb4=New-Object byte[] 4096; $rnd=New-Object Random;" ^
  "    $sw=[Diagnostics.Stopwatch]::StartNew(); $n=2000;" ^
  "    for($i=0;$i -lt $n;$i++){ $fs.Position=[long]($rnd.NextDouble()*($sz-4096)); [void]$fs.Read($rb4,0,4096) }" ^
  "    $sw.Stop(); $fs.Close();" ^
  "    $iops=[math]::Round($n/$sw.Elapsed.TotalSeconds,0); $rand=[math]::Round($iops*4096/1MB,2);" ^
  "    Remove-Item $p -Force -EA SilentlyContinue;" ^
  "    '{0,-22} seq_write {1,7} MB/s | seq_read {2,7} MB/s | 4K-rand {3,6} MB/s ({4} IOPS)' -f $k,$w,$r,$rand,$iops" ^
  "  } catch { '{0,-22} ERR {1}' -f $k,$_.Exception.Message.Substring(0,[Math]::Min(60,$_.Exception.Message.Length)) } }" >> "%OUT%" 2>&1

echo. >> "%OUT%"
echo --- G: physical disk identity --- >> "%OUT%"
powershell -NoProfile -Command "Get-Disk | Where-Object {$_.Number -ne $null} | Select-Object Number,FriendlyName,BusType,@{n='GB';e={[math]::Round($_.Size/1GB)}},PartitionStyle | Format-Table -AutoSize | Out-String -Width 160" >> "%OUT%" 2>&1
echo. >> "%OUT%"
echo --- NIC link speed (is this box even at gigabit?) --- >> "%OUT%"
powershell -NoProfile -Command "Get-NetAdapter | Where-Object Status -eq 'Up' | Select-Object Name,InterfaceDescription,LinkSpeed | Format-Table -AutoSize | Out-String -Width 160" >> "%OUT%" 2>&1
echo. >> "%OUT%"
echo ==== DONE ==== >> "%OUT%"
type "%OUT%"
