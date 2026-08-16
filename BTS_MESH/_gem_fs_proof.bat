@echo off
REM Does Gemini CLI, on the FREE Google sign-in, have real local filesystem access?
REM The API-key env vars are cleared deliberately: with GEMINI_API_KEY set the CLI uses the
REM dead prepay key and 429s. Cleared, it uses the OAuth credential just authorised.
setlocal
set GEMINI_API_KEY=
set GOOGLE_API_KEY=
set GEMINI_CLI_TRUST_WORKSPACE=true
set LOG=V:\Research4\Ai\BTS_MESH\_gem_fs_proof.log

> "%LOG%" echo ==== GEM FS PROOF %DATE% %TIME% ====
>> "%LOG%" echo (free-tier Google sign-in; API keys cleared from the environment)
>> "%LOG%" echo.

cd /d V:\Research4\Ai\BTS_MESH
>> "%LOG%" echo --- PROOF 1: read the probe token from this directory ---
call gemini -p "Read the file _fs_probe.txt in the current directory and reply with ONLY the value after the equals sign. No other words." --approval-mode yolo >> "%LOG%" 2>&1
>> "%LOG%" echo exit=%ERRORLEVEL%

>> "%LOG%" echo.
>> "%LOG%" echo --- PROOF 2: reach the actual research tree ---
cd /d V:\Research4
call gemini -p "Does a file named BU.MD exist in this directory? Reply with only YES or NO." --approval-mode yolo >> "%LOG%" 2>&1
>> "%LOG%" echo exit=%ERRORLEVEL%

>> "%LOG%" echo.
>> "%LOG%" echo --- which model / tier is it actually using? ---
cd /d V:\Research4\Ai\BTS_MESH
call gemini -p "Reply with only the name of the model answering this." --approval-mode yolo >> "%LOG%" 2>&1
>> "%LOG%" echo exit=%ERRORLEVEL%
endlocal
