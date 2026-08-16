#!/usr/bin/env python3
r"""
drive_inventory.py - enumerate a tree's METADATA only. No file is ever opened.

WHY THIS SHAPE, 2026-07-31
    G: reads at 1.1 MB/s. Its metadata, however, enumerates fine - the benchmark
    found 4,688 files over 20 MB in 45 seconds. So the whole triage question
    ("what is on G: that exists nowhere else?") can be answered for FREE, by
    comparing inventories, and only then do we spend the expensive reads on the
    files that turn out to be unique.

    Reading a dying drive to decide what to read off it is backwards.

*** READ-ONLY, and stronger than that: NO FILE IS OPENED AT ALL. ***
    Only os.scandir + DirEntry.stat(), which come from the directory entry.

Long paths: every path is emitted \\?\-prefixed on Windows, because the tree
this was built for nests directories that encode their own absolute path as a
filename (measured: 478 of 605 paths >= 260 chars).

Usage:
    py -3.14 drive_inventory.py "G:\Tera 4 - back 24" --out V:\...\G_INVENTORY.csv
    py -3.14 drive_inventory.py --selftest
"""

import argparse
import csv
import os
import sys
import time
from datetime import datetime
from pathlib import Path

LONG = "\\\\?\\"


def _long_prefix(p):
    """The PURE rule, with no platform gate — so it can be tested anywhere.
    Splitting these was forced by the selftest: the combined version asserted
    Windows behaviour and therefore FAILED on Linux, where the function is
    correctly a no-op. A test that fails on a healthy platform is a broken
    test, and it would have been 'fixed' by weakening the assertion."""
    if not p or p.startswith(LONG):
        return p
    if len(p) > 1 and p[1] == ":":
        return LONG + p
    return p


def longpath(p):
    return _long_prefix(p) if os.name == "nt" else p


def shortpath(p):
    return p[len(LONG):] if p.startswith(LONG) else p


def walk(root, on_tick=None, tick_every=5000):
    """Yield (path, size, mtime). Never opens a file. Survives permission errors
    and unreadable directories - and COUNTS them, because a directory we could
    not enter is not the same as an empty one."""
    stack = [longpath(str(root))]
    n = 0
    errors = []
    while stack:
        d = stack.pop()
        try:
            with os.scandir(d) as it:
                for e in it:
                    try:
                        if e.is_dir(follow_symlinks=False):
                            stack.append(e.path)
                            continue
                        st = e.stat(follow_symlinks=False)
                        n += 1
                        if on_tick and n % tick_every == 0:
                            on_tick(n, len(errors))
                        yield (shortpath(e.path), st.st_size, st.st_mtime)
                    except OSError as ex:
                        errors.append((shortpath(e.path), str(ex)[:80]))
        except OSError as ex:
            errors.append((shortpath(d), str(ex)[:80]))
    if on_tick:
        on_tick(n, len(errors))
    walk.errors = errors


walk.errors = []


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("root", nargs="?")
    ap.add_argument("--out", default="")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()

    if args.selftest:
        import tempfile
        d = Path(tempfile.mkdtemp())
        (d / "a").mkdir()
        (d / "a" / "x.txt").write_text("hello")
        (d / "y.bin").write_bytes(b"0" * 1234)
        rows = list(walk(d))
        names = sorted(os.path.basename(p) for p, _, _ in rows)
        sizes = {os.path.basename(p): s for p, s, _ in rows}
        ok = names == ["x.txt", "y.bin"] and sizes["y.bin"] == 1234 and sizes["x.txt"] == 5
        print("  walks a tree, sizes correct, no file opened:  %s" % ("PASS" if ok else "*** FAIL ***"))
        ok2 = (_long_prefix(r"C:\a") == r"\\?\C:\a"
               and _long_prefix(r"\\?\C:\a") == r"\\?\C:\a"      # idempotent
               and _long_prefix("/tmp/x") == "/tmp/x"            # non-drive untouched
               and shortpath(r"\\?\C:\a") == r"C:\a")
        print("  long-path rule (pure, any platform):          %s" % ("PASS" if ok2 else "*** FAIL ***"))
        ok3 = longpath(r"C:\a") == (r"\\?\C:\a" if os.name == "nt" else r"C:\a")
        print("  platform gate (no-op off Windows):            %s" % ("PASS" if ok3 else "*** FAIL ***"))
        # a path over MAX_PATH must survive the round trip intact
        deep = "C:\\" + "\\".join("d%03d" % i for i in range(60)) + "\\file.txt"
        ok4 = len(deep) > 260 and shortpath(_long_prefix(deep)) == deep
        print("  >260-char path round-trips (%d chars):        %s" % (len(deep), "PASS" if ok4 else "*** FAIL ***"))
        return 0 if (ok and ok2 and ok3 and ok4) else 1

    if not args.root:
        print("  [!] give me a root, or --selftest")
        return 1
    root = args.root
    out = args.out or ("INVENTORY_%s.csv" % datetime.now().strftime("%Y-%m-%d"))

    print("=" * 74)
    print("  drive_inventory   %s" % root)
    print("  METADATA ONLY - no file is opened. Safe on a failing drive.")
    print("=" * 74)

    t0 = time.perf_counter()
    last = [0.0]

    def tick(n, nerr):
        now = time.perf_counter()
        if now - last[0] > 2.0:
            last[0] = now
            msg = "    {:,} files ... {:.0f}s".format(n, now - t0)
            if nerr:
                msg += "   ({:,} unreadable)".format(nerr)
            print(msg, flush=True)

    total = 0
    tbytes = 0
    Path(os.path.dirname(out) or ".").mkdir(parents=True, exist_ok=True)
    with open(out, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["path", "name", "size", "mtime", "ext"])
        for p, size, mt in walk(root, on_tick=tick):
            total += 1
            tbytes += size
            w.writerow([p, os.path.basename(p), size,
                        datetime.fromtimestamp(mt).strftime("%Y-%m-%d %H:%M:%S"),
                        os.path.splitext(p)[1].lower()])

    dt = time.perf_counter() - t0
    print("-" * 74)
    print("  files      : {:,}".format(total))
    print("  bytes      : {:,}  ({:.1f} GB)".format(tbytes, tbytes / (1 << 30)))
    print("  unreadable : {:,}   <- NOT the same as empty; listed in the log".format(len(walk.errors)))
    print("  elapsed    : {:.1f} s".format(dt))
    print("  inventory  -> %s" % out)
    if walk.errors:
        elog = out + ".errors.txt"
        with open(elog, "w", encoding="utf-8") as fh:
            for p, e in walk.errors[:5000]:
                fh.write("%s\t%s\n" % (p, e))
        print("  errors     -> %s" % elog)
        print("  ⚠ unreadable entries on a FAILING drive are a finding, not noise.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
