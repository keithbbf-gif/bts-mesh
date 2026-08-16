"""
bts_node.py — full-duplex mesh node for ONE agent (cowork / sgh / copilot).
Full duplex = each node sends and receives INDEPENDENTLY over the shared log;
send never blocks on receive. Receive is idempotent (dedupe by message id `mid`)
so a duplicated/re-posted signal is delivered at most once (fault tolerance).
"""
from __future__ import annotations
import os, uuid
import bts_bus as B
import bts_registry as R

class Node:
    def __init__(self, root: str, agent: str):
        self.root = root
        self.agent = agent.upper()
        self.log = os.path.join(root, "BTS_SIGNAL.log")
        self.cursor = os.path.join(root, f".cursor_{self.agent.lower()}")
        self.seen = os.path.join(root, f".seen_{self.agent.lower()}")
        self.registry = os.path.join(root, "SESSION_REGISTRY.json")

    # ---- send side (independent of receive) ----
    def send(self, type_: str, note: str, path: str | None = None, **extra) -> str:
        mid = extra.pop("mid", None) or uuid.uuid4().hex[:12]
        env = B.make_envelope(type_, note, path=path, mid=mid, **extra)
        B.append_signal(self.log, self.agent, env)
        return mid

    # ---- receive side (idempotent; never sees its own) ----
    def _load_seen(self):
        if not os.path.exists(self.seen):
            return set()
        return set(x.strip() for x in open(self.seen) if x.strip())

    def _mark_seen(self, mid):
        with open(self.seen, "a", encoding="utf-8") as f:
            f.write(mid + "\n")

    def receive(self):
        recs = B.read_new_signals(self.log, self.cursor, mine=self.agent)
        seen = self._load_seen()
        out = []
        for r in recs:
            mid = r["env"].get("mid")
            if mid and mid in seen:
                continue                      # idempotent: already handled
            out.append(r)
            if mid:
                self._mark_seen(mid); seen.add(mid)
        return out

    def ack(self, rec, note="ack"):
        return self.send("ACK", note, path=rec["env"].get("path"), ref=rec["env"].get("mid"))

    def heartbeat(self, topic="main", status="active", sid=None):
        R.upsert_session(self.registry, sid or f"{self.agent.lower()}:{topic}",
                         self.agent.lower(), topic, status=status)
