"""
bts_orchestrator.py — the conductor SKELETON for the BTS mesh.
Ties bus + registry + capability routing together. Consumes the append-only
signal log, updates the session registry, and handles SPAWN_SESSION by routing
the topic to the best agent and enqueuing a launch request.

WHAT WORKS HERE: envelope consumption, registry updates, capability routing,
spawn-request queueing, seed-file creation. WHAT IS STUBBED: the actual
"launch a browser session of agent X and seed it" step (`launch_session`) —
that requires the Chrome bridge / a browser driver and is intentionally a
clearly-marked stub so the daemon is safe to run and unit-test now.
"""
from __future__ import annotations
import json, os, argparse
import bts_bus as B
import bts_registry as R

class Orchestrator:
    def __init__(self, root: str, me: str = "ORCH"):
        self.root = root
        self.me = me
        self.log = os.path.join(root, "BTS_SIGNAL.log")
        self.cursor = os.path.join(root, ".cursor_orch")
        self.registry = os.path.join(root, "SESSION_REGISTRY.json")
        self.cards = os.path.join(root, "cards")
        self.spawn_queue = os.path.join(root, "SPAWN_QUEUE.jsonl")

    def tick(self) -> list[dict]:
        """Process all new signals once. Returns actions taken (for tests/logs)."""
        actions = []
        for rec in B.read_new_signals(self.log, self.cursor, mine=self.me):
            env = rec["env"]; t = env["type"]
            if t == "SPAWN_SESSION":
                actions.append(self._handle_spawn(env))
            elif t == "TASK_COMPLETE":
                actions.append({"action": "log_complete", "note": env.get("note")})
            elif t in ("NEEDS_INPUT",):
                actions.append({"action": "surface_to_human", "note": env.get("note")})
            else:
                actions.append({"action": "noop", "type": t})
        return actions

    def _handle_spawn(self, env: dict) -> dict:
        topic = env.get("topic") or env.get("note", "topic")
        tags = env.get("tags") or [topic]
        agent = env.get("agent") or R.route_topic(self.cards, tags) or "grok"
        seed_path = env.get("seed_path") or f"SESSION_SEED_{topic}.md"
        seed_abs = os.path.join(self.root, seed_path)
        if not os.path.exists(seed_abs):
            B.atomic_write(seed_abs, self._seed_template(topic, agent, env.get("note", "")))
        sid = f"{agent}:{topic}"
        R.upsert_session(self.registry, sid, agent, topic,
                         status="requested", tasks=[env.get("note", "")])
        req = {"sid": sid, "agent": agent, "topic": topic, "seed_path": seed_path, "ts": B.utc_now()}
        with open(self.spawn_queue, "a", encoding="utf-8") as f:
            f.write(json.dumps(req) + "\n")
        self.launch_session(req)   # stub
        return {"action": "spawn", **req}

    def launch_session(self, req: dict) -> None:
        # STUB: real impl opens a browser tab for req['agent'] and pastes a
        # pointer to req['seed_path']. Left unimplemented on purpose.
        return None

    @staticmethod
    def _seed_template(topic, agent, note):
        return (f"# SESSION SEED — {topic}\n"
                f"**Spawn for:** {agent}\n**Reason:** {note}\n\n"
                f"## Boot steps\n1. Read this seed.\n2. Read ROLD index + the pointer(s) below.\n"
                f"3. Announce readiness by appending a TASK-style signal to BTS_SIGNAL.log.\n\n"
                f"## Context pointers\n- (fill: ROLD paths this session needs)\n")

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--once", action="store_true")
    a = ap.parse_args()
    orch = Orchestrator(a.root)
    acts = orch.tick()
    print(json.dumps(acts, indent=2))
