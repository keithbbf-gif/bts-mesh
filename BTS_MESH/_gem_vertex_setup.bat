@echo off
REM ============================================================================
REM Point Gemini CLI at VERTEX, because the other two auth paths are dead.
REM 2026-07-27.
REM
REM MEASURED TODAY, all three options in the CLI's own picker:
REM   1. Sign in with Google -> IneligibleTierError, UNSUPPORTED_CLIENT.
REM      Google has retired "Gemini Code Assist for individuals" for this client
REM      and points at the Antigravity suite instead.
REM   2. Gemini API key       -> 429 "prepayment credits are depleted" (billing
REM      state, does NOT reset at midnight).
REM   3. Vertex AI            -> HTTP 200. Proven this afternoon with
REM      x-goog-api-key against aiplatform.
REM
REM So Vertex is not a preference, it is the only surviving path. It also spends
REM the $300 trial credit that expires ~2026-10-13 and is otherwise wasted -
REM "burn the free allotments" is already the standing instruction.
REM
REM WATCH THE COST SHAPE: Vertex bills THINKING tokens at the OUTPUT rate, and
REM they sit outside candidatesTokenCount. One 3-sentence answer once cost 28.5x
REM its visible output. Keep prompts tight and prefer flash.
REM ============================================================================
setlocal
set LOG=V:\Research4\Ai\BTS_MESH\_gem_vertex_setup.log
set SEC=V:\Research4\.secrets

for /f "usebackq delims=" %%K in ("%SEC%\vertex_key.txt") do set VKEY=%%K

set GEMINI_API_KEY=
set GOOGLE_GENAI_USE_VERTEXAI=true
set GOOGLE_API_KEY=%VKEY%
set GEMINI_CLI_TRUST_WORKSPACE=true

> "%LOG%" echo ==== GEM via VERTEX %DATE% %TIME% ====
>> "%LOG%" echo GOOGLE_GENAI_USE_VERTEXAI=true, key from vertex_key.txt
>> "%LOG%" echo.

cd /d V:\Research4\Ai\BTS_MESH
>> "%LOG%" echo --- PROOF 1: read the local probe token ---
call gemini -p "Read the file _fs_probe.txt in the current directory and reply with ONLY the value after the equals sign." --approval-mode yolo -m gemini-2.5-flash >> "%LOG%" 2>&1
>> "%LOG%" echo exit=%ERRORLEVEL%

>> "%LOG%" echo.
>> "%LOG%" echo --- PROOF 2: reach the real research tree ---
cd /d V:\Research4
call gemini -p "Does a file named BU.MD exist in this directory? Reply only YES or NO." --approval-mode yolo -m gemini-2.5-flash >> "%LOG%" 2>&1
>> "%LOG%" echo exit=%ERRORLEVEL%
endlocal
