@echo off
REM Host-side self-test for bts_identity. Run on the HOST, not the sandbox mount:
REM the FUSE mount serves truncated copies and produces FALSE SyntaxErrors (7 hits 2026-07-15).
cd /d "%~dp0"
python bts_identity.py > "%~dp0_identity_selftest.txt" 2>&1
echo exit=%ERRORLEVEL% >> "%~dp0_identity_selftest.txt"
