@echo off
REM Repair the Vertex rail and the GDX consent fuse from stored refresh tokens.
REM Native, because Cowork's sandbox is egress-blocked from googleapis.
setlocal
set PYTHONIOENCODING=utf-8
set MESH=V:\Research4\Ai\BTS_MESH
cd /d "%MESH%"
where py >nul 2>&1 && (set PY=py -3) || (set PY=python)
%PY% "%MESH%\fix_rails.py" > "%MESH%\fix_rails.log" 2>&1
type "%MESH%\fix_rails.log"
endlocal
