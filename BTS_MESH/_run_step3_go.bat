@echo off
cd /d V:\Research4\Ai\BTS_MESH
set OUT=V:\Research4\Ai\BTS_MESH\_migrate_step3_go.txt
echo ==== STEP 3 APPLY %DATE% %TIME% ==== > "%OUT%"
echo   Writes inside V:\Research4 ONLY. V:\Research4 is not touched and remains the live tree. >> "%OUT%"
echo. >> "%OUT%"
python _migrate_step3_paths.py --go >> "%OUT%" 2>&1
echo. >> "%OUT%"
echo --- VERIFY: are there any live V:\Research4 refs left in CODE under V:\Research4? --- >> "%OUT%"
echo   (expect 0 in code/operational; the ~2,746 in history + frozen backups are PRESERVED ON PURPOSE) >> "%OUT%"
python -c "import os,re,io;pat=re.compile(re.escape(r'V:\Research4'),re.I);pat2=re.compile(re.escape('D:\\\\Research2'),re.I);EXT={'.py','.bat','.vbs','.json','.html','.cmd','.ps1'};FROZ=('_backup','00_session_','.bak_','_old');n=0;f_=0;\nimport sys\nfor dp,dn,fn in os.walk(r'V:\Research4'):\n    for x in fn:\n        p=os.path.join(dp,x)\n        if os.path.splitext(x)[1].lower() not in EXT: continue\n        if any(m in p.lower() for m in FROZ): continue\n        try:\n            if os.path.getsize(p)>8*1024*1024: continue\n            t=io.open(p,encoding='utf-8',errors='strict').read()\n        except Exception: continue\n        c=len(pat.findall(t))+len(pat2.findall(t))\n        if c: n+=c; f_+=1; print('   LEFT %4dx  %s'%(c,p[13:]))\nprint('   live D:\\\\Research2 refs remaining in runnable code: %d in %d files'%(n,f_))" >> "%OUT%" 2>&1
echo. >> "%OUT%"
echo --- SANITY: does the rewritten code still parse? --- >> "%OUT%"
python -c "import py_compile,os,sys;bad=0;tot=0;\nfor dp,dn,fn in os.walk(r'V:\Research4\Ai\BTS_MESH'):\n    if any(m in dp.lower() for m in ('_backup','__pycache__')): continue\n    for x in fn:\n        if not x.endswith('.py'): continue\n        tot+=1\n        try: py_compile.compile(os.path.join(dp,x),doraise=True)\n        except Exception as e: bad+=1; print('   *** %s: %s'%(x,str(e)[:90]))\nprint('   BTS_MESH python: %d files, %d failed to compile'%(tot,bad))" >> "%OUT%" 2>&1
echo. >> "%OUT%"
echo --- bts_paths from the NEW tree --- >> "%OUT%"
cd /d V:\Research4\Ai\BTS_MESH
python bts_paths.py >> "%OUT%" 2>&1
echo. >> "%OUT%"
echo ==== DONE ==== >> "%OUT%"
type "%OUT%"
