"""
bts_discovery.py — self-improving discovery, modeled on TidyUP2's append-only
"Classes discovered" list. Each conductor cycle scans the live log (and,
RETROACTIVELY, the prior session's log in case the monitor wasn't run) for NEW
classes it hasn't seen — signal types, file extensions, agents — records them
append-only to MESH_DISCOVERED_CLASSES.md, and promotes them into
MESH_KNOWN_CLASSES.json so the next cycle knows them. Nothing is ever silently
dropped: an unknown is surfaced, not lost.
"""
from __future__ import annotations
import os, json, datetime
import bts_bus as B

def _utc():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def _known(path):
    if os.path.exists(path):
        try:
            return json.load(open(path, encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    return {"types": [], "ext": [], "agents": []}

def _scan(log_path, known_types):
    found = {"types": set(), "ext": set(), "agents": set()}
    if not os.path.exists(log_path):
        return found
    for line in open(log_path, encoding="utf-8"):
        rec = B._parse_line(line)
        if not rec:
            continue
        found["agents"].add(rec["agent"])
        t = rec["env"].get("type")
        if t and t not in known_types:
            found["types"].add(t)
        p = rec["env"].get("path") or ""
        base = os.path.basename(p)
        if "." in base:
            found["ext"].add(os.path.splitext(base)[1].lower())
    return found

def discover_and_record(root, prior_log=None):
    known_path = os.path.join(root, "MESH_KNOWN_CLASSES.json")
    disc_md = os.path.join(root, "MESH_DISCOVERED_CLASSES.md")
    known = _known(known_path)
    known_types = set(known["types"]) | set(B.VALID_TYPES)

    logs = [os.path.join(root, "BTS_SIGNAL.log")]
    if prior_log and os.path.exists(prior_log):
        logs.append(prior_log)                      # retroactive catch-up

    agg = {"types": set(), "ext": set(), "agents": set()}
    for lg in logs:
        f = _scan(lg, known_types)
        for k in agg:
            agg[k] |= f[k]
    for k in agg:                                    # subtract already-known
        agg[k] -= set(known.get(k, []))

    additions = {k: sorted(v) for k, v in agg.items() if v}
    if additions:
        with open(disc_md, "a", encoding="utf-8") as f:
            if os.path.getsize(disc_md) == 0 if os.path.exists(disc_md) else True:
                f.write("# MESH — Classes Discovered (append-only, TidyUP2-style)\n")
            f.write(f"- **{_utc()}** discovered: {json.dumps(additions)}\n")
        for k, v in additions.items():
            known[k] = sorted(set(known.get(k, [])) | set(v))
        B.atomic_write(known_path, json.dumps(known, indent=2))
    return additions
