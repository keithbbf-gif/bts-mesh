r"""
parallel_jobs.py — run queue work CONCURRENTLY, and serialize the writes that cannot be. 2026-08-16.

KEITH, 2026-08-16: "Run the jobs simultaneously. You have multiple agents and Ais."

He is right that the bottleneck is real. `bts_runner` claims ONE job per tick, so a 12-minute
publish blocks everything behind it, and tonight that meant two one-minute fixes waited on a winget
install. `mesh_fanout` has proven the parallel pattern for MODELS since 04:00 — six families, 17
seconds of wall clock instead of the sum. Nothing carried that pattern across to JOBS.

🔴 BUT "RUN THEM ALL AT ONCE" IS WRONG AS STATED, AND THE REASON IS WORTH WRITING DOWN.
   Several of tonight's jobs end by doing the same three things: append to TOOLS_REGISTRY.json, run
   tools_sync --write, run bts_health. Run two of those concurrently and you get a lost update on
   the registry, or two processes rewriting 00_TOOLS_INDEX.md at once. This mesh has spent the night
   fixing control files that could not be parsed; racing two writers at them would be the most
   expensive possible way to save ninety seconds.

⇒ SO THE RULE IS: FAN OUT THE WORK, FUNNEL THE WRITES.
     PARALLEL  anything that only reads, or writes files nobody else touches — model calls, probes,
               selftests, per-lane fixes on distinct modules, installs.
     SERIAL    TOOLS_REGISTRY.json · tools_sync · rails.toml · bts_health · scars.py --rebuild.
               One writer, after the fan-out, once.

   That is the same shape as the mesh itself: several families answer at once, one process judges
   and writes. The concurrency belongs to the work, not to the bookkeeping.
"""
import concurrent.futures as cf
import os
import subprocess
import sys
import time

MESH = os.path.dirname(os.path.abspath(__file__))

# Files that make a job a SERIAL job if it touches them. Any of these in the source text and the
# job is excluded from the parallel pool — detected mechanically, not by remembering to label it.
SERIAL_MARKERS = ("TOOLS_REGISTRY.json", "tools_sync", "rails.toml", "bts_health",
                  "scars.py", "bts_kdash_feed", "verify_pointers")


def classify(path):
    """Return 'serial' if the job writes shared control state, else 'parallel'.

    ⚠ It reads the SOURCE, not a label. A job that forgets to declare itself still gets classified
    correctly, which is the only way this holds up when somebody writes a job at 3 a.m.
    """
    try:
        txt = open(path, encoding="utf-8", errors="replace").read()
    except Exception:                                                 # noqa: BLE001
        return "serial"                                               # unreadable -> assume unsafe
    return "serial" if any(m in txt for m in SERIAL_MARKERS) else "parallel"


def run_one(path, timeout=1800):
    t0 = time.time()
    try:
        p = subprocess.run(["py", "-3.14", path], capture_output=True, timeout=timeout)
        out = (p.stdout or b"").decode("utf-8", "replace") + (p.stderr or b"").decode("utf-8", "replace")
        return {"job": os.path.basename(path), "rc": p.returncode,
                "secs": round(time.time() - t0, 1), "tail": out.strip()[-600:]}
    except subprocess.TimeoutExpired:
        return {"job": os.path.basename(path), "rc": 124,
                "secs": round(time.time() - t0, 1), "tail": "TIMED OUT"}
    except Exception as e:                                            # noqa: BLE001
        return {"job": os.path.basename(path), "rc": 99,
                "secs": round(time.time() - t0, 1), "tail": str(e)[:300]}


def run(paths, max_workers=6, verbose=True):
    par = [p for p in paths if classify(p) == "parallel"]
    ser = [p for p in paths if classify(p) == "serial"]
    results = []
    t0 = time.time()
    if verbose:
        print("  parallel (%d): %s" % (len(par), ", ".join(os.path.basename(p) for p in par) or "-"))
        print("  serial   (%d): %s" % (len(ser), ", ".join(os.path.basename(p) for p in ser) or "-"))
        print("  serial jobs touch shared control state; running them concurrently would race the")
        print("  registry and the index, which is the one thing not worth saving a minute on.")
    if par:
        with cf.ThreadPoolExecutor(max_workers=min(max_workers, len(par))) as ex:
            for r in ex.map(run_one, par):
                results.append(r)
                if verbose:
                    print("  %-34s rc=%-3s %6.1fs" % (r["job"], r["rc"], r["secs"]))
    for p in ser:
        r = run_one(p)
        results.append(r)
        if verbose:
            print("  %-34s rc=%-3s %6.1fs  (serial)" % (r["job"], r["rc"], r["secs"]))
    wall = round(time.time() - t0, 1)
    total = round(sum(r["secs"] for r in results), 1)
    if verbose:
        print("\n  wall clock %.1fs  ·  sum of parts %.1fs  ·  saved %.1fs"
              % (wall, total, max(total - wall, 0)))
    return {"results": results, "wall": wall, "sum": total}


def selftest():
    """Prove the classifier BOTH ways, because a classifier that only ever says 'serial' is safe
    and useless, and one that only ever says 'parallel' is fast and destructive."""
    import tempfile
    d = tempfile.mkdtemp()
    a = os.path.join(d, "reads_only.py")
    open(a, "w").write("print('hello')\n")
    b = os.path.join(d, "writes_registry.py")
    open(b, "w").write("open('TOOLS_REGISTRY.json')\n")
    ok = classify(a) == "parallel" and classify(b) == "serial"
    print("  read-only job  -> %s (want parallel)" % classify(a))
    print("  registry job   -> %s (want serial)" % classify(b))
    missing = os.path.join(d, "gone.py")
    ok &= classify(missing) == "serial"
    print("  unreadable job -> %s (want serial: unknown means unsafe)" % classify(missing))
    print("SELFTEST %s" % ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


if __name__ == "__main__":
    if "--selftest" in sys.argv or len(sys.argv) == 1:
        raise SystemExit(selftest())
    raise SystemExit(0 if run([a for a in sys.argv[1:] if a.endswith(".py")])["results"] else 1)
