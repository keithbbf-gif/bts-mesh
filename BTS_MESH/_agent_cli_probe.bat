@echo off
REM What agent CLIs already exist on this machine? Report only; install nothing.
setlocal
set LOG=V:\Research4\Ai\BTS_MESH\_agent_cli_probe.log
> "%LOG%" echo ==== AGENT CLI PROBE  %DATE% %TIME% ====
for %%C in (node npm npx grok gemini copilot gh claude) do (
  >> "%LOG%" echo.
  >> "%LOG%" echo --- %%C ---
  where %%C  >> "%LOG%" 2>&1
)
>> "%LOG%" echo.
>> "%LOG%" echo --- versions ---
node -v  >> "%LOG%" 2>&1
npm -v   >> "%LOG%" 2>&1
>> "%LOG%" echo.
>> "%LOG%" echo --- npm global list ---
npm ls -g --depth=0 >> "%LOG%" 2>&1
>> "%LOG%" echo.
>> "%LOG%" echo --- config dirs ---
if exist "%USERPROFILE%\.grok"   (>> "%LOG%" echo .grok PRESENT)   else (>> "%LOG%" echo .grok absent)
if exist "%USERPROFILE%\.gemini" (>> "%LOG%" echo .gemini PRESENT) else (>> "%LOG%" echo .gemini absent)
if exist "%USERPROFILE%\.copilot" (>> "%LOG%" echo .copilot PRESENT) else (>> "%LOG%" echo .copilot absent)
endlocal
