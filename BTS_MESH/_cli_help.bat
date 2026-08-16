@echo off
setlocal
set LOG=V:\Research4\Ai\BTS_MESH\_cli_help.log
> "%LOG%" echo ==== CLI HELP %DATE% %TIME% ====
>> "%LOG%" echo.
>> "%LOG%" echo ################ grok --help ################
grok --help >> "%LOG%" 2>&1
>> "%LOG%" echo.
>> "%LOG%" echo ################ grok mcp --help ################
grok mcp --help >> "%LOG%" 2>&1
endlocal
