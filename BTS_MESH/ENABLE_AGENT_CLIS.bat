@echo off
REM ============================================================================
REM ENABLE_AGENT_CLIS.bat  --  authenticate the local agent CLIs and PROVE each
REM one can read this machine's filesystem.   rev 2, 2026-07-27
REM
REM The point of these CLIs is LOCAL FILE ACCESS. "Installed" proves nothing.
REM Each agent is asked a question it can only answer by reading a file on V:
REM containing a token no model could know. Answer it -> the node has genuinely
REM escaped the chat window.
REM
REM rev 1 used invented flags (--no-interactive) and failed on syntax, not on
REM capability. Real syntax, from `grok --help`:
REM     grok -p "<prompt>" --cwd <dir> --always-approve
REM Gemini refuses untrusted dirs headlessly unless GEMINI_CLI_TRUST_WORKSPACE=true.
REM
REM Keys come from .secrets and are never echoed.
REM ============================================================================
setlocal EnableDelayedExpansion
set MESH=V:\Research4\Ai\BTS_MESH
set SEC=V:\Research4\.secrets
set LOG=%MESH%\enable_agent_clis.log
set PROBE=%MESH%\_fs_probe.txt

> "%LOG%" echo ==== ENABLE AGENT CLIS rev2  %DATE% %TIME% ====

REM The proof token. No model can produce this without reading the file.
> "%PROBE%" echo KMESH-FS-PROOF-TOKEN=QUILLFEATHER-7731-ORANGERY

for /f "usebackq delims=" %%K in ("%SEC%\Grok_API_Token-Key.txt") do set XAI_API_KEY=%%K
for /f "usebackq delims=" %%K in ("%SEC%\gemini_key.txt") do set GEMINI_API_KEY=%%K
set GEMINI_CLI_TRUST_WORKSPACE=true

echo.
echo   Proving local filesystem access for each node.
echo   Log: %LOG%
echo.

REM ---------------------------------------------------------------- GW
>> "%LOG%" echo.
>> "%LOG%" echo ######## GW / Grok Build ########
grok --version >> "%LOG%" 2>&1
>> "%LOG%" echo --- models visible to the CLI ---
grok models >> "%LOG%" 2>&1
>> "%LOG%" echo.
>> "%LOG%" echo --- FS PROOF: read _fs_probe.txt and echo the token ---
echo   [GW ] Grok Build reading a local file...
grok -p "Read the file _fs_probe.txt in the current directory and reply with ONLY the value after the equals sign. No other words." --cwd "%MESH%" --always-approve >> "%LOG%" 2>&1
>> "%LOG%" echo exit=!ERRORLEVEL!
>> "%LOG%" echo.
>> "%LOG%" echo --- MCP servers configured ---
grok mcp list >> "%LOG%" 2>&1

REM ---------------------------------------------------------------- GEM
>> "%LOG%" echo.
>> "%LOG%" echo ######## GEM / Gemini CLI ########
cd /d "%MESH%"
call gemini --version >> "%LOG%" 2>&1
>> "%LOG%" echo --- FS PROOF ---
echo   [GEM] Gemini CLI reading a local file...
call gemini -p "Read the file _fs_probe.txt in the current directory and reply with ONLY the value after the equals sign. No other words." --approval-mode yolo >> "%LOG%" 2>&1
>> "%LOG%" echo exit=!ERRORLEVEL!

REM ---------------------------------------------------------------- CoP
REM MEASURED 2026-07-26: github.com/copilot/agents returns "Copilot is unavailable
REM to you at this time" for PapaFig1. Run it anyway so the answer is definitive.
>> "%LOG%" echo.
>> "%LOG%" echo ######## CoP / Copilot CLI ########
call copilot --version >> "%LOG%" 2>&1
echo   [CoP] Copilot CLI (expected to need a subscription)...
call copilot -p "say OK" --allow-all-tools >> "%LOG%" 2>&1
>> "%LOG%" echo exit=!ERRORLEVEL!

echo.
echo   Done. See %LOG%
echo.
endlocal
