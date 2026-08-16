@echo off
REM ============================================================================
REM INSTALL_AGENT_CLIS.bat  --  local agent CLIs for the KMesh nodes.
REM Created 2026-07-27 by Cowork.
REM
REM WHY: these CLIs run ON THIS MACHINE with direct filesystem access and native
REM MCP support. That is categorically different from the chat/API legs the mesh
REM has been using. A node with local FS access can read V:\Research4 itself
REM instead of having Cowork courier file contents through a prompt.
REM
REM   GW  -> Grok Build   (xAI, included with SuperGrok)   ALREADY INSTALLED
REM   GEM -> Gemini CLI   (Google, free tier w/ Google acct)
REM   CoP -> Copilot CLI  (GitHub, REQUIRES a Copilot subscription - see below)
REM
REM Installs nothing that is already present. Logs everything.
REM ============================================================================
setlocal
set LOG=V:\Research4\Ai\BTS_MESH\install_agent_clis.log
> "%LOG%" echo ==== AGENT CLI INSTALL  %DATE% %TIME% ====

echo.
echo   Installing local agent CLIs. This takes a few minutes.
echo   Log: %LOG%
echo.

REM ---------------------------------------------------------------- GW / Grok Build
>> "%LOG%" echo.
>> "%LOG%" echo ######## GROK BUILD (GW) ########
where grok >nul 2>&1
if %ERRORLEVEL%==0 (
  echo   [GW ] Grok Build already installed - checking version
  >> "%LOG%" echo already installed:
  where grok >> "%LOG%" 2>&1
  grok --version >> "%LOG%" 2>&1
) else (
  echo   [GW ] installing Grok Build...
  >> "%LOG%" echo installing via official PowerShell installer
  powershell -NoProfile -ExecutionPolicy Bypass -Command "irm https://x.ai/cli/install.ps1 | iex" >> "%LOG%" 2>&1
)

REM ---------------------------------------------------------------- GEM / Gemini CLI
>> "%LOG%" echo.
>> "%LOG%" echo ######## GEMINI CLI (GEM) ########
where gemini >nul 2>&1
if %ERRORLEVEL%==0 (
  echo   [GEM] Gemini CLI already installed
  >> "%LOG%" echo already installed
  gemini --version >> "%LOG%" 2>&1
) else (
  echo   [GEM] installing Gemini CLI via npm...
  call npm install -g @google/gemini-cli >> "%LOG%" 2>&1
  >> "%LOG%" echo exit=%ERRORLEVEL%
)

REM ---------------------------------------------------------------- CoP / Copilot CLI
REM MEASURED 2026-07-26: this account (PapaFig1) has NO Copilot subscription.
REM github.com/copilot/agents redirects to signup and returns "Copilot is
REM unavailable to you at this time". The CLI installs fine but cannot
REM authenticate without a paid plan, so it is installed ONLY as a probe -
REM the useful output is a definitive answer, not a working node.
>> "%LOG%" echo.
>> "%LOG%" echo ######## COPILOT CLI (CoP) ########
>> "%LOG%" echo NOTE: PapaFig1 had no Copilot subscription as of 2026-07-26.
where copilot >nul 2>&1
if %ERRORLEVEL%==0 (
  echo   [CoP] Copilot CLI already installed
  >> "%LOG%" echo already installed
) else (
  echo   [CoP] installing Copilot CLI via npm...
  call npm install -g @github/copilot >> "%LOG%" 2>&1
  >> "%LOG%" echo exit=%ERRORLEVEL%
)

REM ---------------------------------------------------------------- report
>> "%LOG%" echo.
>> "%LOG%" echo ######## FINAL STATE ########
for %%C in (grok gemini copilot) do (
  >> "%LOG%" echo --- %%C ---
  where %%C >> "%LOG%" 2>&1
)
>> "%LOG%" echo.
>> "%LOG%" echo --- npm global ---
call npm ls -g --depth=0 >> "%LOG%" 2>&1

echo.
echo   Done. See %LOG%
echo.
endlocal
