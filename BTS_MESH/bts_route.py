"""
bts_route.py — cost-aware capability routing over nodes/*.json.
Among nodes whose good_at overlaps the topic tags, pick the LOWEST cost;
tie-break by (weight * overlap) descending. This is the token/agent-optimization
lever: reserve the expensive node (cowork/Opus) for tasks only it can do.
"""
from __future__ import annotations
import os, json

def route(nodes_dir: str, tags):
    tags = set(t.lower() for t in tags)
    cands = []
    if not os.path.isdir(nodes_dir):
        return None
    for fn in os.listdir(nodes_dir):
        if not fn.endswith(".json"):
            continue
        c = json.load(open(os.path.join(nodes_dir, fn), encoding="utf-8"))
        overlap = len(set(t.lower() for t in c.get("good_at", [])) & tags)
        if overlap > 0:
            # sort key: cheapest first, then most-capable (higher weight*overlap)
            cands.append((float(c.get("cost", 1.0)),
                          -float(c.get("weight", 1.0)) * overlap,
                          c["agent"]))
    if not cands:
        return None
    cands.sort()
    return cands[0][2]
