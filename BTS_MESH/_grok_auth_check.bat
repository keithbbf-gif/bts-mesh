@echo off
REM Did `grok login` land, and does the SUBSCRIPTION path expose more models than
REM the metered API key did? XAI_API_KEY is deliberately cleared: with it set, the
REM CLI uses the API (billed per token) and reported only grok-4.5.
setlocal
set XAI_API_KEY=
set LOG=V:\Research4\Ai\BTS_MESH\_grok_auth_check.log
set MESH=V:\Research4\Ai\BTS_MESH

> "%LOG%" echo ==== GROK AUTH CHECK %DATE% %TIME% ====
>> "%LOG%" echo (XAI_API_KEY cleared - this is the OAuth/subscription path)
>> "%LOG%" echo.
>> "%LOG%" echo --- models ---
grok models >> "%LOG%" 2>&1
>> "%LOG%" echo.
>> "%LOG%" echo --- credential files in %%USERPROFILE%%\.grok ---
dir /b "%USERPROFILE%\.grok" >> "%LOG%" 2>&1
>> "%LOG%" echo.
>> "%LOG%" echo --- FS PROOF on the subscription path ---
grok -p "Read _fs_probe.txt in the current directory and reply with ONLY the value after the equals sign." --cwd "%MESH%" --always-approve >> "%LOG%" 2>&1
>> "%LOG%" echo exit=%ERRORLEVEL%
>> "%LOG%" echo.
>> "%LOG%" echo --- can it reach the ACTUAL research tree? ---
grok -p "List the names of any files matching BU.MD in this directory. Reply with just the filename, or NONE." --cwd "V:\Research4" --always-approve >> "%LOG%" 2>&1
>> "%LOG%" echo exit=%ERRORLEVEL%
endlocal
