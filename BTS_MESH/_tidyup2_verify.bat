@echo off
REM TIDYUP2 verification sweep — Cowork 2026-07-16.
REM T2 check #2: referenced-file existence. EVERY file claimed this session must exist at the stated
REM path with a non-trivial size. Claims verified here, not trusted.
REM T2 check #3: number-consistency (docx page count vs the subagent's "20 pages" claim).
REM RULE BEING APPLIED: "never accept an agent's DONE" — the docx was built by a subagent.
setlocal
set "OUT=%~dp0_tidyup2_verify.txt"
> "%OUT%" echo ===== TIDYUP2 VERIFY  %DATE% %TIME% =====

>> "%OUT%" echo.
>> "%OUT%" echo --- [T2-2] FILES CLAIMED THIS SESSION (size + date; 0 bytes or MISSING = a lie) ---
for %%F in (
  "V:\Research4\Ai\BTS_MESH\bts_identity.py"
  "V:\Research4\Ai\BTS_MESH\_identity_selftest.txt"
  "V:\Research4\Ai\BTS_MESH\_sysinfo.txt"
  "V:\Research4\Ai\BTS_MESH\_drivehealth.txt"
  "V:\Research4\Ai\BTS_MESH\JMESH_TRAIN_S1_FIREBOX_2026-07-15.docx"
  "V:\Research4\Ai\00_NEXT_SESSION_HANDOFF_2026-07-15.md"
  "V:\Research4\Ai\00_ROLD_COMMANDS_TidyUp_BootUp.md"
  "V:\Research4\CLAUDE.md"
) do (
  if exist %%F ( for %%A in (%%F) do >> "%OUT%" echo   OK      %%~zA bytes  %%~tA  %%~nxA ) else ( >> "%OUT%" echo   MISSING !!!!!!!!  %%F )
)

>> "%OUT%" echo.
>> "%OUT%" echo --- [T2-3] DOCX PAGE COUNT — the subagent CLAIMED 20. Verify from the file itself. ---
>> "%OUT%" echo     (docProps/app.xml carries Word's own Pages count)
powershell -NoProfile -Command "$f='V:\Research4\Ai\BTS_MESH\JMESH_TRAIN_S1_FIREBOX_2026-07-15.docx'; if(Test-Path $f){ Add-Type -AssemblyName System.IO.Compression.FileSystem; $z=[System.IO.Compression.ZipFile]::OpenRead($f); $e=$z.Entries | Where-Object {$_.FullName -eq 'docProps/app.xml'}; if($e){ $r=New-Object System.IO.StreamReader($e.Open()); $x=[xml]$r.ReadToEnd(); 'Pages   = ' + $x.Properties.Pages; 'Words   = ' + $x.Properties.Words; 'Company = ' + $x.Properties.Company } else {'no app.xml (docx-js often omits it - page count then only knowable by rendering)'}; $img=($z.Entries | Where-Object {$_.FullName -like 'word/media/*'}).Count; 'Embedded images in word/media = ' + $img; $z.Dispose() } else {'DOCX MISSING'}" >> "%OUT%" 2>&1

>> "%OUT%" echo.
>> "%OUT%" echo --- [T2-3b] DOCX internal sanity: is it a real zip w/ document.xml? ---
powershell -NoProfile -Command "$f='V:\Research4\Ai\BTS_MESH\JMESH_TRAIN_S1_FIREBOX_2026-07-15.docx'; if(Test-Path $f){ Add-Type -AssemblyName System.IO.Compression.FileSystem; $z=[System.IO.Compression.ZipFile]::OpenRead($f); $z.Entries | Where-Object {$_.FullName -eq 'word/document.xml'} | ForEach-Object { 'word/document.xml = ' + $_.Length + ' bytes uncompressed' }; 'total zip entries = ' + $z.Entries.Count; $z.Dispose() }" >> "%OUT%" 2>&1

>> "%OUT%" echo.
>> "%OUT%" echo --- [T2-5] MEMORY: does the new file exist and does MEMORY.md index it? ---
set "MEM=C:\Users\Papa\AppData\Roaming\Claude\local-agent-mode-sessions\598a803e-7ed8-4011-8c6f-36b1139ced47\ccd03d6b-a1bb-44c5-a4d3-100b4b78f91f\spaces\2fad0f5a-db93-49fb-911d-4f047c3ff5a3\memory"
if exist "%MEM%\project_hardware_truth_2026-07-15.md" ( >> "%OUT%" echo   OK      memory file exists ) else ( >> "%OUT%" echo   MISSING memory file )
findstr /C:"project_hardware_truth_2026-07-15" "%MEM%\MEMORY.md" >nul 2>&1 && ( >> "%OUT%" echo   OK      MEMORY.md indexes it ) || ( >> "%OUT%" echo   MISSING MEMORY.md index line )

>> "%OUT%" echo.
>> "%OUT%" echo --- [T2-8] LIVING DOCS: pointer must name the NEWEST handoff on disk ---
>> "%OUT%" echo   Handoffs present:
dir /b /o-n "V:\Research4\Ai\00_NEXT_SESSION_HANDOFF_*.md" 2>nul >> "%OUT%"
>> "%OUT%" echo   ROLD pointer line says:
findstr /C:"READ FIRST" "V:\Research4\Ai\00_ROLD_COMMANDS_TidyUp_BootUp.md" >> "%OUT%" 2>&1
>> "%OUT%" echo   CLAUDE.md pointer line says:
findstr /C:"00_NEXT_SESSION_HANDOFF" "V:\Research4\CLAUDE.md" >> "%OUT%" 2>&1

>> "%OUT%" echo.
>> "%OUT%" echo --- [T2-x] G: — did the backup mirror come back? ---
powershell -NoProfile -Command "$g=Get-Volume -DriveLetter G -ErrorAction SilentlyContinue; if($g){ 'G: PRESENT — {0} — {1:N1} GB free of {2:N1}' -f $g.FileSystemLabel,($g.SizeRemaining/1GB),($g.Size/1GB) } else { 'G: STILL ABSENT — the Tera-4 backup mirror is NOT mounted' }" >> "%OUT%" 2>&1

>> "%OUT%" echo.
>> "%OUT%" echo ===== END =====
endlocal
