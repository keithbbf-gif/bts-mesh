@echo off
REM ── JDash verification burst (Cowork, 2026-07-14) ────────────────────────────────
REM Emits a spread of REAL test events across several actors/surfaces through the
REM intact host-side bts_state.py (append-only log + atomic projection rebuild, with
REM the 5 s lock). Used to prove the dashboard's 1 s seq-gated poll drives all four
REM panels on real traffic, then goes still when the burst stops. Safe to delete.
cd /d "V:\Research4\Ai\BTS_MESH"
echo === JDASH TEST BURST %DATE% %TIME% === > _jdash_test_emit.log

python bts_state.py --emit COWORK SGH dom_send "test: verify JDash burst" out >> _jdash_test_emit.log 2>&1
timeout /t 2 /nobreak >nul
python bts_state.py --emit SGH GDX gdx_write "handoff_2026-07-14.md" out >> _jdash_test_emit.log 2>&1
timeout /t 2 /nobreak >nul
python bts_state.py --emit GEM COWORK read "verify claim batch reply" in >> _jdash_test_emit.log 2>&1
timeout /t 2 /nobreak >nul
python bts_state.py --emit COWORK ITC publish "ai.dchambers.com subtree" out >> _jdash_test_emit.log 2>&1
timeout /t 2 /nobreak >nul
python bts_state.py --emit COWORK CROSSREF crossref_hit "10.1088/0953-8984/20/38/382202" out >> _jdash_test_emit.log 2>&1

echo === DONE %TIME% === >> _jdash_test_emit.log
