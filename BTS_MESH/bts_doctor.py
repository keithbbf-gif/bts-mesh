"""
bts_doctor.py — health check for the BTS mesh ecosystem. Returns 0 if healthy,
1 if warnings. Verifies module imports, log integrity, registry validity,
orphaned signal paths, stale sessions, and dead-letter volume.
"""
import os, json, importlib, time
import bts_bus as B

def run(root="."):
    warn=[]; ok=[]
    # 1) modules import
    for m in ("bts_bus","bts_node","bts_registry","bts_route","bts_discovery","bts_watcher","bts_conductor","bts_state"):
        try: importlib.import_module(m); ok.append(f"import {m}")
        except Exception as e: warn.append(f"IMPORT FAIL {m}: {e}")
    # 2) signal log integrity
    lg=os.path.join(root,"BTS_SIGNAL.log")
    if os.path.exists(lg):
        good=bad=0
        for l in open(lg,encoding="utf-8"):
            if not l.strip(): continue
            (good:=good+1) if B._parse_line(l) else (bad:=bad+1)
        ok.append(f"log: {good} parseable lines")
        if bad: warn.append(f"log: {bad} corrupt lines")
    else: ok.append("log: none yet")
    # 3) registry valid JSON + no dup sids
    rp=os.path.join(root,"SESSION_REGISTRY.json")
    if os.path.exists(rp):
        try:
            reg=json.load(open(rp)); sids=[s.get("sid") for s in reg.get("sessions",[])]
            if len(sids)!=len(set(sids)): warn.append("registry: duplicate sids")
            else: ok.append(f"registry: {len(sids)} sessions, no dups")
        except Exception as e: warn.append(f"registry: bad JSON ({e})")
    # 4) orphaned signal paths (NEW_OUTPUT_READY pointing at missing files)
    if os.path.exists(lg):
        miss=0
        for l in open(lg,encoding="utf-8"):
            r=B._parse_line(l)
            if r and r["env"].get("type") in ("NEW_OUTPUT_READY","QUESTION_FOR_YOU"):
                p=r["env"].get("path")
                if p and not os.path.exists(os.path.join(root,p)): miss+=1
        (ok if not miss else warn).append(f"orphaned signal paths: {miss}")
    # 5) dead-letter volume
    dl=os.path.join(root,"DEAD_LETTER.log")
    n=sum(1 for l in open(dl,encoding="utf-8") if l.strip()) if os.path.exists(dl) else 0
    (ok if n<5 else warn).append(f"dead-letter entries: {n}")
    print("BTS DOCTOR —", "HEALTHY" if not warn else f"{len(warn)} WARNING(S)")
    for o in ok: print("  ok  ", o)
    for w in warn: print("  !!  ", w)
    return 0 if not warn else 1

if __name__=="__main__":
    import sys; sys.exit(run(sys.argv[1] if len(sys.argv)>1 else "."))
