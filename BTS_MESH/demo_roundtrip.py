"""
demo_roundtrip.py — shows the full BTS loop with no chat UI, no network.
Run: python3 demo_roundtrip.py
"""
import os, tempfile, json
import bts_bus as B
from bts_orchestrator import Orchestrator

root = tempfile.mkdtemp(prefix="bts_demo_")
os.makedirs(os.path.join(root, "cards"), exist_ok=True)
for a,tags in [("grok",["web-search","github"]),("claude",["verification","synthesis"])]:
    json.dump({"agent":a,"good_at":tags,"weight":1.0},
              open(os.path.join(root,"cards",a+".json"),"w"))
log = os.path.join(root,"BTS_SIGNAL.log")
print(f"ROLD root: {root}\n")

# 1) Grok stages a deliverable ATOMICALLY, then signals.
deliv = os.path.join(root,"SGH_returns","BTS-B_toolkit_mining.md")
B.atomic_write(deliv, "# Batch B\n(real content here)\n")
B.append_signal(log,"SGH",B.make_envelope("NEW_OUTPUT_READY",
                "Batch B mining done", path="SGH_returns/BTS-B_toolkit_mining.md"))
print("1. Grok -> NEW_OUTPUT_READY (deliverable written atomically)")

# 2) Claude side consumes new signals (filters its own), reads the file, ACKs.
cur = os.path.join(root,".cursor_claude")
for rec in B.read_new_signals(log, cur, mine="CLA"):
    e = rec["env"]
    if e["type"]=="NEW_OUTPUT_READY":
        body = open(os.path.join(root,e["path"])).read()
        print(f"2. Claude read {e['path']} ({len(body)} bytes) -> integrating")
        B.append_signal(log,"CLA",B.make_envelope("ACK","read+integrated Batch B",
                        path=e["path"]))

# 3) Grok asks the orchestrator to spawn a session for the next topic.
B.append_signal(log,"SGH",B.make_envelope("SPAWN_SESSION","kick off Batch C prototype",
                topic="orchestrator-proto", tags=["code","github"]))
print("3. Grok -> SPAWN_SESSION(orchestrator-proto)")

# 4) Orchestrator ticks: routes, seeds, registers, queues launch.
orch = Orchestrator(root)
for a in orch.tick():
    print("4. Orchestrator:", json.dumps(a))
print("\nRegistry:", open(os.path.join(root,"SESSION_REGISTRY.json")).read())
print("Signal log:"); print(open(log).read())
