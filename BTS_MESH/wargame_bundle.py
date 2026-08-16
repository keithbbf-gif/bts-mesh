#!/usr/bin/env python3
"""
wargame_bundle.py - concatenate the built record into ONE attachable file for the DOM lane.

WHY THIS IS A FILE AND NOT A ONE-LINER IN THE BAT
  It was a one-liner twice, and cmd mangled it twice on 2026-08-02:

    1. `%` - cmd consumes percent signs, so a Python %-format string arrives half-eaten.
       Rewritten with concatenation to avoid it.
    2. `!` - with `setlocal EnableDelayedExpansion`, cmd treats `!` as a variable delimiter and
       ATE THE MIDDLE OF THE LINE. `if p.name != '00_INDEX.txt'` became `if p.name ` and Python
       reported a SyntaxError pointing at text that was never in the source.

  The second one is the instructive failure: fixing the first hazard did nothing about the second,
  because the real defect was never the escape character - it was inlining a program into a shell
  that has its own opinions about punctuation.

  ⇒ RULE: the `.py` in the tree is the tool; the `.bat` is delivery. Never inline Python in cmd.

USAGE
    py -3.14 wargame_bundle.py
    py -3.14 wargame_bundle.py --selftest
"""
from __future__ import annotations
import argparse, sys
import pathlib
from datetime import datetime
from pathlib import Path

RECORD = Path(r"V:\Ai\Legal\WARGAME\record")
OUT    = Path(r"V:\Ai\Legal\WARGAME\RECORD_ALL.txt")


def bundle(record: Path, out: Path) -> int:
    if not record.is_dir():
        print(f"  no record at {record} - build it first (menu option 1)")
        return 2
    import re as _re
    _BUNDLE = _re.compile(r'^\d{2}_[A-Z_]+__')     # whitelist, same rule as wargame.load_record
    docs = sorted(p for p in record.glob("*.txt") if _BUNDLE.match(p.name))
    stray = [p.name for p in record.glob("*.txt") if not _BUNDLE.match(p.name)]
    if stray:
        print(f"  whitelist kept OUT: {', '.join(sorted(stray))}")
    if not docs:
        print(f"  {record} is empty - build the record first (menu option 1)")
        return 2

    parts, total = [], 0
    for p in docs:
        declared = p.stat().st_size
        raw = p.read_bytes()
        if len(raw) != declared:      # the mount's silent short-read signature
            print(f"  ABORT - TRUNCATED READ on {p.name}: {len(raw)} B vs {declared} B declared")
            print("  A partial record attached to four browser sessions would look completely")
            print("  normal and be wrong. Nothing written.")
            return 3
        parts.append("\n\n===== DOCUMENT: " + p.name + " =====\n"
                     + raw.decode("utf-8", "replace"))
        total += declared

    text = "".join(parts)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text, encoding="utf-8")

    back = out.stat().st_size
    print(f"  {len(docs)} documents  {len(text):,} chars  ~{len(text)//4:,} tokens")
    print(f"  -> {out}  ({back:,} B on disk)")
    if back < total // 2:
        print("  ⚠ the file on disk is far smaller than what was read. Do not attach it.")
        return 3
    return 0


def selftest() -> int:
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        r = Path(d) / "record"; r.mkdir()
        (r / "01_A.txt").write_text("alpha", encoding="utf-8")
        (r / "02_B.txt").write_text("beta", encoding="utf-8")
        (r / "00_INDEX.txt").write_text("INDEX - must not be bundled", encoding="utf-8")
        o = Path(d) / "ALL.txt"
        assert bundle(r, o) == 0
        t = o.read_text(encoding="utf-8")
        assert "alpha" in t and "beta" in t, "documents missing"
        assert "must not be bundled" not in t, "the index leaked into the record"
        assert t.count("===== DOCUMENT:") == 2, "wrong document count"
    print("  selftest: 2 docs bundled, index excluded, delimiters intact - PASS")
    return 0


# ---------------------------------------------------------------- console log
class _Tee:
    """Mirror everything printed to a log file.

    Keith, 2026-08-02: "Those are transient on the desktop, always deleted after run - be sure you
    are writing logs, I can't always paste the output."

    The Desktop bat is deleted the moment it finishes, and its console goes with it. So the LOG IS
    THE ONLY RECORD OF WHAT HAPPENED. Logging belongs in the tool, not the wrapper - a wrapper that
    is thrown away cannot be the thing that remembers. Line-buffered and flushed on every write, so
    a crash or a closed window still leaves everything up to the failure.
    """

    def __init__(self, path, stream):
        self.path, self.stream = pathlib.Path(path), stream
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.fh = self.path.open("a", encoding="utf-8", errors="replace")
        self.fh.write(f"\n\n{'='*78}\n### RUN {datetime.now():%Y-%m-%d %H:%M:%S}  "
                      f"{' '.join(sys.argv)}\n{'='*78}\n")
        self.fh.flush()

    def write(self, s):
        self.stream.write(s)
        try:
            self.fh.write(s); self.fh.flush()
        except Exception:
            pass
        return len(s)

    def flush(self):
        self.stream.flush()
        try:
            self.fh.flush()
        except Exception:
            pass


def start_log(path):
    sys.stdout = _Tee(path, sys.__stdout__)
    sys.stderr = _Tee(path, sys.__stderr__)
    print(f"  logging to {path}")


def main() -> int:
    start_log(OUT.parent / "_BUNDLE_LOG.txt")
    ap = argparse.ArgumentParser()
    ap.add_argument("--record", default=str(RECORD))
    ap.add_argument("--out", default=str(OUT))
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    return bundle(Path(a.record), Path(a.out))


if __name__ == "__main__":
    sys.exit(main())
