import os, sys, shutil, tempfile, time, json
sys.path.insert(0, "/tmp/bts_mesh")
import bts_bus as B, bts_registry as R, bts_discovery as D
from bts_node import Node
from bts_route import route
from bts_conductor import Conductor

fails=[]
def check(n,c): print(("  PASS " if c else "  FAIL ")+n); (fails.append(n) if not c else None)

root=tempfile.mkdtemp(prefix="v2_")
shutil.copytree("/tmp/bts_mesh/nodes", os.path.join(root,"nodes"))
log=os.path.join(root,"BTS_SIGNAL.log")

print("== FULL DUPLEX: two nodes send + receive independently ==")
cowork=Node(root,"COWORK"); sgh=Node(root,"SGH")
sgh.send("NEW_OUTPUT_READY","batch done",path="SGH_returns/x.md")
cowork.send("QUESTION_FOR_YOU","which figure?",path="ROLD/q.md")
cw_in=cowork.receive(); sg_in=sgh.receive()
check("cowork sees only sgh's msg (not its own)", len(cw_in)==1 and cw_in[0]["env"]["type"]=="NEW_OUTPUT_READY")
check("sgh sees only cowork's msg (not its own)", len(sg_in)==1 and sg_in[0]["env"]["type"]=="QUESTION_FOR_YOU")

print("== IDEMPOTENCY: duplicate mid delivered once ==")
mid=sgh.send("STATUS","progress 50%")           # cowork will read
dup_env=B.make_envelope("STATUS","progress 50% (reposted)", mid=mid)
B.append_signal(log,"SGH",dup_env)              # same mid, reposted
got=cowork.receive()
statuses=[r for r in got if r["env"]["type"]=="STATUS"]
check("reposted same-mid STATUS delivered once", len(statuses)==1)

print("== FAULT TOLERANCE: unknown + ERROR -> dead-letter, no crash ==")
# hand-craft an unknown-type line (bypass validation) + a proper ERROR
with open(log,"a") as f:
    f.write('SGH|{"mid":"zz1","type":"WAT_IS_THIS","note":"???","ts":"2026-07-10T00:00:00Z"}\n')
sgh.send("ERROR","rclone console closed unexpectedly")
orch=Conductor(root, me="ORCH")
acts=orch.tick()
check("unknown type dead-lettered", any(a.get("action")=="dead_letter" for a in acts))
check("ERROR parked", any(a.get("action")=="error_parked" for a in acts))
check("DEAD_LETTER.log written", os.path.exists(os.path.join(root,"DEAD_LETTER.log")))

print("== COST-AWARE ROUTING (token/agent optimization) ==")
check("web/github -> sgh (cheap)", route(os.path.join(root,"nodes"),["github","web-search"])=="sgh")
check("verify/synthesis -> cowork (only capable)", route(os.path.join(root,"nodes"),["verification","synthesis"])=="cowork")
check("office/excel -> copilot", route(os.path.join(root,"nodes"),["excel","office"])=="copilot")

print("== SPAWN routes by tags + seeds ==")
sgh.send("SPAWN_SESSION","kick lit sweep", topic="lit", tags=["literature","web-search"])
a2=orch.tick()
sp=[a for a in a2 if a.get("action")=="spawn"]
check("spawn routed to sgh", sp and sp[0]["agent"]=="sgh")
check("seed file created", os.path.exists(os.path.join(root,"SESSION_SEED_lit.md")))

print("== REAP STALE sessions ==")
reg=os.path.join(root,"SESSION_REGISTRY.json")
R.upsert_session(reg,"cowork:old","cowork","old",status="active")
# backdate its ts
d=R.load_registry(reg)
for s in d["sessions"]:
    if s["sid"]=="cowork:old": s["ts"]="2026-07-10T00:00:00Z"
R._save(reg,d)
orch.ttl=1
reaped=orch.reap_stale()
check("old active session reaped -> stale", "cowork:old" in reaped)

print("== SELF-IMPROVING DISCOVERY (TidyUP2-style) + retroactive ==")
# prior-session log with a novel type + novel ext, simulating a missed monitor run
prior=os.path.join(root,"PRIOR_SIGNAL.log")
with open(prior,"w") as f:
    f.write('SGH|{"mid":"p1","type":"HANDSHAKE","note":"hi","path":"x/y.parquet","ts":"2026-07-09T00:00:00Z"}\n')
add=D.discover_and_record(root, prior_log=prior)
check("discovered novel type HANDSHAKE (retroactive)", "HANDSHAKE" in add.get("types",[]))
check("discovered novel ext .parquet", ".parquet" in add.get("ext",[]))
check("MESH_DISCOVERED_CLASSES.md appended", os.path.exists(os.path.join(root,"MESH_DISCOVERED_CLASSES.md")))
check("MESH_KNOWN_CLASSES.json promoted", "HANDSHAKE" in json.load(open(os.path.join(root,"MESH_KNOWN_CLASSES.json")))["types"])
# second run: already-known, no re-discovery
add2=D.discover_and_record(root, prior_log=prior)
check("no re-discovery of known classes", add2=={})

print(); print("RESULT:", "ALL PASS" if not fails else f"{len(fails)} FAIL -> {fails}")
sys.exit(1 if fails else 0)
