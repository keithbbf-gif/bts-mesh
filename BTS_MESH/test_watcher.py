import os, sys, tempfile, threading, time
sys.path.insert(0,"/tmp/bts_mesh")
import bts_bus as B, bts_watcher as W
fails=[]
def check(n,c): print(("  PASS " if c else "  FAIL ")+n); (fails.append(n) if not c else None)

root=tempfile.mkdtemp(prefix="watch_"); wdir=os.path.join(root,"bus")
hits=[]; stop=threading.Event()
def onchg(fp,ev): hits.append((os.path.basename(fp),ev))
backend={}
def run(): backend["b"]=W.watch(wdir,onchg,interval=0.2,stop_event=stop,timeout=5,once=True)
th=threading.Thread(target=run,daemon=True); th.start()
time.sleep(0.5)
B.atomic_write(os.path.join(wdir,"BTS_SIGNAL_new.md"),"hi")   # atomic create -> final name only
time.sleep(0.6); stop.set(); th.join(timeout=3)
check("watcher (poll) detected new file", any(h[0]=="BTS_SIGNAL_new.md" for h in hits))
check("used polling backend (watchdog absent)", backend.get("b")=="poll")
check("only final name seen, no .tmp_ event", not any(h[0].startswith(".tmp_") for h in hits))
print(); print("RESULT:", "ALL PASS" if not fails else f"{len(fails)} FAIL -> {fails}")
sys.exit(1 if fails else 0)
