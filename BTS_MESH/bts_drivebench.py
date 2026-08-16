#!/usr/bin/env python3
"""
bts_drivebench.py — measure REAL read/write speed of every surface the mesh uses, and write the
numbers into dash.json so the CAPACITY panel can show them next to the drive list.

WHY IT EXISTS (Keith, 2026-07-13): the mesh moves payloads across very different media — local NVMe,
a spinning USB mirror, Google Drive (GDX), OneDrive (ODX), Cloudflare R2 (ITC). The routing decision
("request over the DOM, reply over GDX") only makes sense if you know what each rail actually costs in
seconds. Guessing is how we ended up pasting 20k-token payloads into the context window.

MEASURED, NOT ASSUMED. A number that was not measured renders as "?" — never as a plausible value.

Run on the HOST (it needs the real drive letters; the Linux sandbox has none).
    python bts_drivebench.py            # bench everything, update dash.json
    python bts_drivebench.py --quick    # 8 MB payload instead of 64 MB
"""
import json, os, sys, time, tempfile, shutil

HERE = os.path.dirname(os.path.abspath(__file__))
DASH = os.path.join(HERE, "dash.json")

# The surfaces the mesh actually uses. label -> a directory we may write a temp file into.
SURFACES = [
    ("C: system",        r"C:\Users\Papa\AppData\Local\Temp"),
    # 2026-07-31: V: had NEVER been benchmarked. The row below was labelled "D: Research2" while
    # already pointing at V:\Research4 — a stale LABEL on a live path, so every reading of that
    # number since the 07-17 tree move has been attributed to the wrong drive.
    ("V: Ai (PRIMARY)",  r"V:\Ai"),
    ("V: Research4",     r"V:\Research4\Ai\PhD2_DATA_ARCHIVE\00_WORKING"),
    ("D: PhD library",   r"D:\PhD"),
    ("X: GDX (Drive)",   r"X:\My Drive\BTS_SGH_Handoff"),   # Google Drive is X:, not E: (Keith, 2026-07-13)
    ("X: GDX root",      r"X:\My Drive"),
    ("ODX (OneDrive)",   r"D:\ODX\OneDrive\BTS_ODX"),
    ("G: Tera mirror",   r"G:\Tera 4 - back 24"),
]

def bench(path, mb=64):
    """Sequential write then read of an mb-sized payload. Returns (write MB/s, read MB/s) or None."""
    if not os.path.isdir(path):
        return None
    payload = os.urandom(1 << 20)          # 1 MB of incompressible data — defeats sync-client dedupe
    fn = os.path.join(path, "_bts_bench_%d.tmp" % os.getpid())
    try:
        t0 = time.perf_counter()
        with open(fn, "wb", buffering=0) as f:
            for _ in range(mb):
                f.write(payload)
            f.flush()
            os.fsync(f.fileno())           # force it to the medium, not just the OS cache
        tw = time.perf_counter() - t0

        # drop what we can of the cache by reopening; on Windows this is imperfect but consistent
        t0 = time.perf_counter()
        n = 0
        with open(fn, "rb", buffering=0) as f:
            while True:
                b = f.read(1 << 20)
                if not b:
                    break
                n += len(b)
        tr = time.perf_counter() - t0
        return (mb / tw if tw > 0 else None, (n / (1 << 20)) / tr if tr > 0 else None)
    except Exception as e:
        return ("ERR", str(e)[:60])
    finally:
        try:
            if os.path.exists(fn):
                os.remove(fn)
        except Exception:
            pass

def main():
    mb = 8 if "--quick" in sys.argv else 64
    out = {}
    print("%-18s %12s %12s" % ("surface", "write MB/s", "read MB/s"))
    print("-" * 44)
    for label, path in SURFACES:
        r = bench(path, mb)
        if r is None:
            out[label] = {"write": None, "read": None, "note": "not present"}
            print("%-18s %12s %12s   (not present)" % (label, "-", "-"))
            continue
        if r[0] == "ERR":
            out[label] = {"write": None, "read": None, "note": r[1]}
            print("%-18s %12s %12s   ERR %s" % (label, "-", "-", r[1]))
            continue
        w, rd = r
        out[label] = {"write": round(w, 1), "read": round(rd, 1), "mb": mb,
                      "ts": time.strftime("%Y-%m-%dT%H:%M:%S")}
        print("%-18s %12.1f %12.1f" % (label, w, rd))

    # OWN FILE (drives.json), NOT dash.json — bts_snapshot rebuilds dash.json on every launch and
    # would erase this. The snapshot merges drives.json in. (Bug found 2026-07-13.)
    DRV = os.path.join(HERE, "drives.json")
    payload = {"drives": out, "measured_at": time.strftime("%Y-%m-%dT%H:%M:%S")}
    tmp = DRV + ".tmp"
    json.dump(payload, open(tmp, "w", encoding="utf-8"), indent=1)
    os.replace(tmp, DRV)           # atomic
    print("\nwrote %d surfaces into %s (merged into dash.json by bts_snapshot)" % (len(out), DRV))

if __name__ == "__main__":
    main()
