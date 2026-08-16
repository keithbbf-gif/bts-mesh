@echo off
set OUT=V:\Research4\Ai\BTS_MESH\_verify_prov.txt
set DIR=V:\Research4\Ai\BTS_MESH\JMESH_TRAIN_S1_build_provenance
echo ==== PROVENANCE COPY VERIFY %DATE% %TIME% ==== > "%OUT%"
echo Comparing HOST md5 against the sandbox-side md5 of /tmp/build (the FUSE cp is the suspect). >> "%OUT%"
echo. >> "%OUT%"

powershell -NoProfile -Command "$exp = @{ 'build.js'='ea9cbf5e6f9485cda319c93a5b341d9a'; 'figs1.py'='128cb916745e44f1f48d4506589c7c4a'; 'figs10.py'='46292de8f19a79fa78f405467a318af2'; 'figs1b.py'='ef91c9bffa918d49d1c0bfe9f11392cd'; 'figs2.py'='86de5ce9d04f776d79c6713b16695800'; 'figs3.py'='847ae96cde884a630c9e5493513dc00a'; 'figs4.py'='ed7742594a54e7b4155179d4e6ee57ac'; 'figs5.py'='5353edc6cd901bc36c9ec2899137801f'; 'figs6.py'='9f080847d30c950f59b8ba34b8477ec2'; 'figs7.py'='0eceb9cf180249d0d7765a660c8eb504'; 'figs8.py'='d68e2bd5f765ccd38947ef9a0c5c9960'; 'figs9.py'='1a3233bcffd0aed4180fad78c6708030'; 'package.json'='a0c0b0752c7b3027a301e04f72785e03' }; $bad=0; foreach($k in ($exp.Keys | Sort-Object)){ $p = 'V:\Research4\Ai\BTS_MESH\JMESH_TRAIN_S1_build_provenance\'+$k; if(Test-Path $p){ $h=(Get-FileHash $p -Algorithm MD5).Hash.ToLower(); if($h -eq $exp[$k]){ '{0,-16} OK    {1}' -f $k,$h } else { $bad++; '{0,-16} *** CORRUPT *** host={1} expected={2}' -f $k,$h,$exp[$k] } } else { $bad++; '{0,-16} *** MISSING ***' -f $k } }; ''; 'FILES BAD = ' + $bad" >> "%OUT%" 2>&1

echo. >> "%OUT%"
echo --- NEGATIVE CONTROL: hash a file we KNOW differs against build.js's expected md5 --- >> "%OUT%"
powershell -NoProfile -Command "$h=(Get-FileHash 'V:\Research4\Ai\BTS_MESH\JMESH_TRAIN_S1_build_provenance\figs1.py' -Algorithm MD5).Hash.ToLower(); $v = if($h -eq 'ea9cbf5e6f9485cda319c93a5b341d9a'){'MATCH (BAD - check is blind!)'}else{'MISMATCH (correct - check CAN detect corruption)'}; 'figs1.py vs build.js expected -> ' + $v" >> "%OUT%" 2>&1

echo. >> "%OUT%"
echo --- img/ PNG count + total bytes --- >> "%OUT%"
powershell -NoProfile -Command "$f=Get-ChildItem 'V:\Research4\Ai\BTS_MESH\JMESH_TRAIN_S1_build_provenance\img' -File; 'files: ' + $f.Count + '  bytes: ' + ($f | Measure-Object -Property Length -Sum).Sum" >> "%OUT%" 2>&1

echo. >> "%OUT%"
echo --- delivered docx still present + size --- >> "%OUT%"
powershell -NoProfile -Command "$p='V:\Research4\Ai\BTS_MESH\JMESH_TRAIN_S1_FIREBOX_2026-07-15.docx'; if(Test-Path $p){ 'docx bytes = ' + (Get-Item $p).Length + '   (sandbox /tmp/build/out.docx = 2696439)' } else { 'DOCX MISSING' }" >> "%OUT%" 2>&1

echo. >> "%OUT%"
echo ==== DONE ==== >> "%OUT%"
