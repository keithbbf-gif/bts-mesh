"""
bts_launch.py — the two-layer launch_session for the BTS mesh.

The Python conductor CANNOT drive a vendor chat UI (no API, auth-gated), so a
spawn is split:
  PREPARE (this module, local Python): write the SESSION_SEED + append a spawn
    request to SPAWN_QUEUE.jsonl (status="pending") + register the session.
  EXECUTE (the bridge layer = Cowork/Claude via the Chrome extension): poll the
    queue, open a new chat for the target agent, paste the seed, mark the queue
    row status="seeded". The new node signals "booted" by writing a first line
    back onto the bus (an ACK / TASK-style signal), which flips status="active".

This module owns PREPARE and the queue bookkeeping. The bridge owns the browser.
"""
from __future__ import annotations
import os, json
import bts_bus as B
import bts_registry as R

SEED_TMPL = """<!-- HANDOFF HEADER -->
**SUMMARY:** boot seed for {agent} on topic '{topic}'.
**OPEN_QUESTIONS:** (node fills)
**CONFIDENCE:** [P]
---
You are being SPAWNED as a fresh node in Keith's BTS mesh. This is your SESSION SEED.
ROLE: {role}
CONTEXT POINTERS: {pointers}
BOOT: reply with a HANDOFF HEADER at the top to confirm you booted, then do the task.
TASK: {task}
"""

def prepare_spawn(root, agent, topic, role="mesh node", task="acknowledge boot",
                  pointers="(see ROLD index)", transport="chrome-bridge"):
    """PREPARE half: seed + queue + registry. Returns the spawn record."""
    seed_rel = f"SESSION_SEED_{topic}.md"
    seed_abs = os.path.join(root, seed_rel)
    if not os.path.exists(seed_abs):
        B.atomic_write(seed_abs, SEED_TMPL.format(agent=agent, topic=topic, role=role,
                                                  pointers=pointers, task=task))
    sid = f"{agent}:{topic}"
    R.upsert_session(os.path.join(root, "SESSION_REGISTRY.json"), sid, agent, topic,
                     status="requested", tasks=[task])
    rec = {"sid": sid, "agent": agent, "topic": topic, "transport": transport,
           "seed_path": seed_rel, "status": "pending", "ts": B.utc_now()}
    with open(os.path.join(root, "SPAWN_QUEUE.jsonl"), "a", encoding="utf-8") as f:
        f.write(json.dumps(rec) + "\n")
    # announce the spawn on the bus
    B.append_signal(os.path.join(root, "BTS_SIGNAL.log"), "ORCH",
                    B.make_envelope("SPAWN_SESSION", f"spawn {agent} on {topic}",
                                    path=seed_rel, agent=agent, topic=topic))
    return rec

def pending_spawns(root):
    """EXECUTE half (bridge reads this): return queue rows still needing a browser launch."""
    q = os.path.join(root, "SPAWN_QUEUE.jsonl")
    if not os.path.exists(q): return []
    out = []
    for l in open(q, encoding="utf-8"):
        if l.strip():
            try: r = json.loads(l)
            except json.JSONDecodeError: continue
            if r.get("status") == "pending": out.append(r)
    return out

def mark_seeded(root, sid):
    """Bridge calls this after it has opened+seeded the session (rewrites the queue)."""
    q = os.path.join(root, "SPAWN_QUEUE.jsonl")
    if not os.path.exists(q): return
    rows = []
    for l in open(q, encoding="utf-8"):
        if not l.strip(): continue
        r = json.loads(l)
        if r.get("sid") == sid and r.get("status") == "pending": r["status"] = "seeded"
        rows.append(r)
    B.atomic_write(q, "\n".join(json.dumps(r) for r in rows) + "\n")
    R.set_status(os.path.join(root, "SESSION_REGISTRY.json"), sid, "seeded")

def mark_booted(root, sid):
    """Called when the new node writes its first signal back onto the bus."""
    R.set_status(os.path.join(root, "SESSION_REGISTRY.json"), sid, "active")

import uuid as _uuid, time as _time, datetime as _dt

def new_spawn_id():
    return _uuid.uuid4().hex[:12]

def claim_spawn(root, sid, by="COWORK"):
    """Bridge claims a pending spawn before acting, so a second bridge/watchdog can't double-spawn."""
    q=os.path.join(root,"SPAWN_QUEUE.jsonl")
    if not os.path.exists(q): return False
    rows=[]; claimed=False
    for l in open(q,encoding="utf-8"):
        if not l.strip(): continue
        r=json.loads(l)
        if r.get("sid")==sid and r.get("status")=="pending":
            r["status"]="claimed"; r["claimed_by"]=by; claimed=True
        rows.append(r)
    if claimed:
        B.atomic_write(q, "\n".join(json.dumps(r) for r in rows)+"\n")
        B.append_signal(os.path.join(root,"BTS_SIGNAL.log"), by,
                        B.make_envelope("STATUS", f"claimed spawn {sid}"))
    return claimed

def stale_pending(root, ttl=90):
    """Python surfaces spawns the bridge did not seed within ttl seconds (re-queue / manual fallback)."""
    q=os.path.join(root,"SPAWN_QUEUE.jsonl")
    if not os.path.exists(q): return []
    now=_time.time(); stale=[]
    for l in open(q,encoding="utf-8"):
        if not l.strip(): continue
        r=json.loads(l)
        if r.get("status") in ("pending","claimed"):
            try:
                age=now-_dt.datetime.strptime(r.get("ts",""),"%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=_dt.timezone.utc).timestamp()
            except Exception: age=0
            if age>ttl: stale.append(r)
    return stale
