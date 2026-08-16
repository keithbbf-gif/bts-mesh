import os, sys, json, shutil, tempfile, threading, time
sys.path.insert(0, "/tmp/bts_mesh")
import bts_bus as B, bts_registry as R, bts_watcher as W
from bts_orchestrator import Orchestrator

fails=[]
def check(n,c):
    print(("  PASS " if c else "  FAIL ")+n);  fails.append(n) if not c else None

root = tempfile.mkdtemp(prefix="mesh_")
shutil.copytree("/tmp/bts_mesh/cards", os.path.join(root, "cards"))
log = os.path.join(root, "BTS_SIGNAL.log")

print("== capability routing ==")
check("web/github -> grok", R.route_topic(os.path.join(root,"cards"), ["github","web-search"])=="grok")
check("verify/synthesis -> claude", R.route_topic(os.path.join(root,"cards"), ["verification","synthesis"])=="claude")

print("== registry upsert/status ==")
R.upsert_session(os.path.join(root,"SESSION_REGISTRY.json"), "claude:main","claude","main",status="active")
check("active topic tracked", "main" in R.active_topics(os.path.join(root,"SESSION_REGISTRY.json")))

print("== orchestrator handles SPAWN_SESSION end-to-end ==")
# Grok requests a spawn for a lit sweep (no explicit agent -> should route by tags)
B.append_signal(log, "SGH", B.make_envelope("SPAWN_SESSION","need a lit sweep session",
                 topic="litsweep", tags=["web-search","literature"]))
B.append_signal(log, "SGH", B.make_envelope("NEEDS_INPUT","blocked on calibration ruling"))
orch = Orchestrator(root)
acts = orch.tick()
spawn = [a for a in acts if a.get("action")=="spawn"]
check("spawn action produced", len(spawn)==1)
check("routed to grok by tags", spawn[0]["agent"]=="grok")
check("seed file created", os.path.exists(os.path.join(root, spawn[0]["seed_path"])))
check("spawn queued", os.path.exists(os.path.join(root,"SPAWN_QUEUE.jsonl")))
check("registry has requested session", any(s["sid"]=="grok:litsweep" for s in R.load_registry(os.path.join(root,"SESSION_REGISTRY.json"))["sessions"]))
check("NEEDS_INPUT surfaced", any(a.get("action")=="surface_to_human" for a in acts))
# idempotent: second tick sees nothing new
check("cursor prevents reprocessing", orch.tick()==[])

print("== watcher polling fallback fires on new file ==")
wdir = os.path.join(root,"watch"); os.makedirs(wdir)
hits=[]
def onchg(fp,ev): hits.append((os.path.basename(fp),ev))
stop=threading.Event()
th=threading.Thread(target=W.watch, kwargs={"dirpath":wdir,"on_change":onchg,"interval":0.2,"stop_event":stop,"timeout":5,"once":True},daemon=True)
th.start(); time.sleep(0.5)
B.atomic_write(os.path.join(wdir,"BTS_SIGNAL_new.md"),"hi")
time.sleep(0.6); stop.set(); th.join(timeout=3)
check("watcher detected new file", any(h[0]=="BTS_SIGNAL_new.md" for h in hits))

print(); print("RESULT:", "ALL PASS" if not fails else f"{len(fails)} FAIL -> {fails}")
sys.exit(1 if fails else 0)
