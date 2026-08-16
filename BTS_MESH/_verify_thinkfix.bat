@echo off
cd /d V:\Research4\Ai\BTS_MESH
set OUT=V:\Research4\Ai\BTS_MESH\_verify_thinkfix.txt
echo ==== THINKING-TOKEN FIX VERIFY %DATE% %TIME% ==== > "%OUT%"
echo   BEFORE: cost = in*Pin + candidates*Pout        (thoughtsTokenCount IGNORED) >> "%OUT%"
echo   AFTER : cost = in*Pin + (candidates+thoughts)*Pout >> "%OUT%"
echo. >> "%OUT%"
python -c "import sys;sys.path.insert(0,r'V:\Research4\Ai\BTS_MESH');from bts_vertex import ask;r=ask('Explain in 3 sentences why the secondary-electron cutoff gives the work function in UPS.',model='gemini-2.5-pro');import json;print(json.dumps({k:r.get(k) for k in ('ok','model','tokens','thinking_ratio','cost_usd')},indent=1));print();print('TEXT:',(r.get('text') or '')[:200])" >> "%OUT%" 2>&1
echo. >> "%OUT%"
echo   ^>^> thinking_ratio ^>1 means MOST of what you paid for was reasoning you never saw. >> "%OUT%"
echo   ^>^> That call is a candidate for the FREE DOM/BTS lane instead. >> "%OUT%"
echo ==== DONE ==== >> "%OUT%"
type "%OUT%"
