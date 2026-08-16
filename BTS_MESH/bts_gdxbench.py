#!/usr/bin/env python3
"""
bts_gdxbench.py — measure the GDX rail as a NODE actually experiences it.

THE DISTINCTION THAT MATTERS (Keith, 2026-07-13):
  bts_drivebench.py measures the write into the LOCAL Google-Drive mount cache on X:. That came out at
  ~580 MB/s — fast, and genuinely useful for us and for GBW (both of which see X: as a local drive).
  But it is NOT what a CLOUD node pays. SGH and GEM live on the far side of Google's servers. For them
  the rail is:  node -> Drive API -> Google storage -> sync daemon -> our X: -> our file tools.
  The latency that governs the mesh is the SYNC leg, and it is invisible to a local disk benchmark.

  Conflating those two numbers would be exactly the "confident number that was never measured" failure
  the dashboard already bit us with. So this script measures the round trip end to end.

WHAT IT MEASURES
  DOWN  (node -> us):  poll X: until a file the node wrote appears; report seconds from the node's
                       stated write time to first-readable-on-disk, and the effective MB/s.
  UP    (us -> node):  write a marker to X:, then the node reports when it can first read it.
                       (This leg needs the node in the loop — the script emits the marker + the exact
                       question to paste.)
  LOCAL (us -> X:):    the same fsync'd write bts_drivebench does, for the side-by-side.

USAGE
  python bts_gdxbench.py --watch <filename>    # DOWN leg: wait for a node's file to land, time it
  python bts_gdxbench.py --marker              # UP leg: drop a timestamped marker for a node to read
  python bts_gdxbench.py --local               # LOCAL leg only
"""
import os, sys, json, time, hashlib

GDX = r"X:\My Drive\BTS_SGH_Handoff"
HERE = os.path.dirname(os.path.abspath(__file__))
DASH = os.path.join(HERE, "dash.json")


def local_leg(mb=64):
    if not os.path.isdir(GDX):
        return {"error": "GDX not present at %s" % GDX}
    payload = os.urandom(1 << 20)
    fn = os.path.join(GDX, "_gdxbench_%d.tmp" % os.getpid())
    t0 = time.perf_counter()
    with open(fn, "wb", buffering=0) as f:
        for _ in range(mb):
            f.write(payload)
        f.flush(); os.fsync(f.fileno())
    tw = time.perf_counter() - t0
    t0 = time.perf_counter()
    n = 0
    with open(fn, "rb", buffering=0) as f:
        while True:
            b = f.read(1 << 20)
            if not b: break
            n += len(b)
    tr = time.perf_counter() - t0
    os.remove(fn)
    return {"write_mbs": round(mb / tw, 1), "read_mbs": round((n / (1 << 20)) / tr, 1), "mb": mb,
            "note": "LOCAL mount cache only — not the cloud round trip"}


def watch(name, timeout=900):
    """DOWN leg. Wait for <name> to appear in GDX and time it."""
    path = os.path.join(GDX, name)
    print("watching %s" % path)
    t0 = time.time()
    while time.time() - t0 < timeout:
        if os.path.exists(path):
            # wait for the size to stop changing — a syncing file appears before it is complete
            last, stable = -1, 0
            while stable < 3:
                sz = os.path.getsize(path)
                if sz == last and sz > 0:
                    stable += 1
                else:
                    stable = 0
                last = sz
                time.sleep(1)
            dt = time.time() - t0
            mb = last / (1 << 20)
            print("\nLANDED after %.1f s   size %.2f MB   -> %.2f MB/s effective (incl. sync)"
                  % (dt, mb, mb / dt if dt else 0))
            print("NOTE: this clock starts when WE started watching, not when the node hit send.")
            print("      For the true node->us latency, ask the node for its write timestamp and")
            print("      subtract. The sync leg is the part a local disk benchmark cannot see.")
            return {"file": name, "seconds": round(dt, 1), "mb": round(mb, 3),
                    "eff_mbs": round(mb / dt, 3) if dt else None}
        time.sleep(2)
    print("TIMEOUT after %d s — nothing landed." % timeout)
    return {"file": name, "seconds": None, "note": "timeout"}


def marker():
    """UP leg. Drop a timestamped marker the node can read back."""
    os.makedirs(GDX, exist_ok=True)
    ts = time.time()
    stamp = time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(ts))
    body = ("GDX RAIL BENCH — UP LEG\n"
            "written_at_epoch: %.3f\nwritten_at_local: %s\n"
            "nonce: %s\n\n"
            "NODE: read this file and reply with (a) this nonce, (b) the epoch time at which you could\n"
            "first read it. We subtract to get the us->node sync latency.\n"
            % (ts, stamp, hashlib.md5(str(ts).encode()).hexdigest()[:12]))
    fn = os.path.join(GDX, "GDX_BENCH_MARKER.txt")
    open(fn, "w", encoding="utf-8").write(body)
    print("wrote %s at %s" % (fn, stamp))
    print("\nPASTE THIS TO THE NODE:\n")
    print("  Read GDX_BENCH_MARKER.txt in BTS_SGH_Handoff. Reply with ONLY: the nonce it contains, and")
    print("  the current epoch time at the moment you could first read it. Nothing else.")
    return {"written_at": ts, "file": fn}


if __name__ == "__main__":
    out = {}
    if "--marker" in sys.argv:
        out["up"] = marker()
    if "--watch" in sys.argv:
        i = sys.argv.index("--watch")
        out["down"] = watch(sys.argv[i + 1] if len(sys.argv) > i + 1 else "BTS-R10_LIT_PDF_2026-07-13.md")
    if "--local" in sys.argv or not out:
        out["local"] = local_leg(8 if "--quick" in sys.argv else 64)
        print(json.dumps(out["local"], indent=1))
    # fold into dash.json under a SEPARATE key — never overwrite the local drive figures with these
    try:
        d = json.load(open(DASH, encoding="utf-8")) if os.path.exists(DASH) else {}
        d.setdefault("gdx_rail", {}).update(out)
        d["gdx_rail"]["measured_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        tmp = DASH + ".tmp"; json.dump(d, open(tmp, "w", encoding="utf-8"), indent=1); os.replace(tmp, DASH)
        print("\nfolded into dash.json -> gdx_rail")
    except Exception as e:
        print("could not update dash.json: %r" % (e,))
