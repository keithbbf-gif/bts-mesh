"""
bts_conductor.py — autonomous v2 conductor. Ties the mesh together:
  * full-duplex node I/O (bts_node)
  * fault tolerance: unknown/ERROR signals go to DEAD_LETTER.log, never crash
  * cost-aware routing of SPAWN_SESSION (bts_route) — token/agent optimization
  * stale-session reaping (liveness)
  * self-improving discovery each cycle (bts_discovery), incl. retroactive prior-log scan
run() wraps tick() in a loop; wrap in bts_watcher.watch for event-driven operation.
launch_session() stays a marked stub (needs the Chrome bridge).
"""
from __future__ import annotations
import os, json, time, datetime
import bts_bus as B, bts_registry as R, bts_discovery as D
from bts_node import Node
from bts_route import route

def _dead_letter(root, agent, env, reason):
    with open(os.path.join(root, "DEAD_LETTER.log"), "a", encoding="utf-8") as f:
        f.write(f"{D._utc()}|{agent}|{reason}|{json.dumps(env)}\n")

def _epoch(ts):
    if not ts:
        return 0.0
    return datetime.datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ").replace(
        tzinfo=datetime.timezone.utc).timestamp()

class Conductor:
    def __init__(self, root, me="ORCH", nodes_dir=None, ttl=900):
        self.root = root
        self.node = Node(root, me)
        self.me = me.upper()
        self.nodes_dir = nodes_dir or os.path.join(root, "nodes")
        self.registry = os.path.join(root, "SESSION_REGISTRY.json")
        self.ttl = ttl

    def reap_stale(self):
        reg = R.load_registry(self.registry)
        now = time.time(); reaped = []
        for s in reg["sessions"]:
            if s.get("status") == "active" and (now - _epoch(s.get("ts"))) > self.ttl:
                s["status"] = "stale"; reaped.append(s["sid"])
        if reaped:
            R._save(self.registry, reg)
        return reaped

    def tick(self, prior_log=None):
        actions = []
        for rec in self.node.receive():
            env = rec["env"]; t = env.get("type"); agent = rec["agent"]
            try:
                if t not in B.VALID_TYPES:
                    _dead_letter(self.root, agent, env, "unknown-type")
                    actions.append({"action": "dead_letter", "type": t})
                elif t == "SPAWN_SESSION":
                    actions.append(self._spawn(env))
                elif t == "ERROR":
                    _dead_letter(self.root, agent, env, "error-signal")
                    actions.append({"action": "error_parked", "note": env.get("note")})
                elif t == "NEEDS_INPUT":
                    actions.append({"action": "surface_to_human", "note": env.get("note")})
                else:
                    actions.append({"action": "noop", "type": t})
            except Exception as e:                       # fault tolerance: never crash the loop
                _dead_letter(self.root, agent, env, f"exc:{e}")
                actions.append({"action": "dead_letter", "reason": str(e)})
        self.reap_stale()
        D.discover_and_record(self.root, prior_log=prior_log)
        return actions

    def _spawn(self, env):
        topic = env.get("topic") or "topic"
        tags = env.get("tags") or [topic]
        agent = env.get("agent") or route(self.nodes_dir, tags) or "sgh"
        seed_rel = env.get("seed_path") or f"SESSION_SEED_{topic}.md"
        seed_abs = os.path.join(self.root, seed_rel)
        if not os.path.exists(seed_abs):
            B.atomic_write(seed_abs, f"# SESSION SEED — {topic}\n**spawn:** {agent}\n"
                                     f"**reason:** {env.get('note','')}\n\n## pointers\n- (fill)\n")
        R.upsert_session(self.registry, f"{agent}:{topic}", agent, topic,
                         status="requested", tasks=[env.get("note", "")])
        self.launch_session(agent, topic, seed_rel)
        return {"action": "spawn", "agent": agent, "topic": topic, "seed_path": seed_rel}

    def launch_session(self, agent, topic, seed_rel):
        # STUB: open a browser session for `agent` and paste a pointer to seed_rel.
        # Needs the Chrome bridge (sgh/copilot) or Cowork-native (cowork). Left unwired.
        return None

    def run(self, cycles=None, interval=2.0, prior_log=None):
        n = 0
        while cycles is None or n < cycles:
            self.tick(prior_log=prior_log)
            n += 1
            if cycles is not None and n >= cycles:
                break
            time.sleep(interval)
