#!/usr/bin/env python3
r"""verify_conf.py — THE CONFIDENCE SCHEMA, ENFORCED.  2026-07-31 (TidyUP2, second pass)

WHY THIS EXISTS
---------------
`rails.toml`'s own header states the schema:

    conf = "V"   measured, with the date it was measured
    conf = "U"   unverified / inferred / vendor-stated — MUST carry `owed` saying how to settle it

**Nothing enforced it, and within one session Cowork violated it in the file that defines it.**

The sequence, 2026-07-31, all inside two hours:
  1. Cowork read `gcloud projects list` (account: keith.bbf@gmail.com), found no such project, and
     wrote a `[[discrepancy]]` saying the project "DOES NOT EXIST" — tagged **conf = "V"**.
  2. TidyUP2 CHECK 4 found `00_HARVEST_2026-07-16.md`: the project is **Joanna's**. Correction made.
  3. TidyUP2 SECOND PASS found the correction had the SAME DEFECT: "it is under joanna.bbf@gmail.com"
     was ALSO tagged **conf = "V"** — while being read out of a 15-day-old document, not measured.
     `bts_vertex.py`'s endpoint carries **no project ID at all**; an API key decides which project is
     billed and that is opaque from this box. Nothing on this machine can confirm it.

⇒ **THE CORRECTION INHERITED THE DEFECT IT CORRECTED.** Being wrong once made me careful about the
FACT and careless about the same TAG. A confidence tag applied by the same habit that produced the
error is not a check on the error.

THE RULE, STATED SO A MACHINE CAN HOLD IT
-----------------------------------------
    conf = "V"  REQUIRES `measured` (a date). "Measured" means an instrument ran and returned this.
                Reading it in a document is NOT measuring it, however trustworthy the document.
    conf = "U"  REQUIRES `owed` (non-empty). An unknown with no stated way to settle it is a wish.

NEGATIVE CONTROL:  python verify_conf.py --selftest
plants (a) conf=V with no date, (b) conf=U with no owed, and asserts both are caught.
A checker never shown to fail is not a checker.
"""
from __future__ import annotations

import datetime as _dt
import os
import sys

try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib

HERE = os.path.dirname(os.path.abspath(__file__))
RAILS = os.path.join(HERE, "rails.toml")

# 🔴 EVERY structured control file, not just rails.toml — Keith, 2026-07-31: "Check all, that's the
# purpose of TU2." The first version of this checker pointed at rails.toml alone, which would have
# enforced the schema exactly where I happened to be looking and nowhere else. A checker with a
# hand-picked scope reproduces the very defect it is meant to catch: an absence that only reflects
# where the search ran. Glob the tree; let new files be covered the day they appear.
import glob as _glob


def all_toml() -> list:
    found = sorted(_glob.glob(os.path.join(HERE, "*.toml")) +
                   _glob.glob(os.path.join(HERE, "**", "*.toml"), recursive=True))
    return sorted(set(found))


VALID = {"V", "U"}


def _walk(obj, path=""):
    """Yield (path, dict) for every table that carries a `conf` key, at any depth."""
    if isinstance(obj, dict):
        if "conf" in obj:
            yield path or "<root>", obj
        for k, v in obj.items():
            yield from _walk(v, f"{path}.{k}" if path else k)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from _walk(v, f"{path}[{i}]")


def check(path: str = RAILS):
    with open(path, "rb") as fh:
        doc = tomllib.load(fh)

    bad, seen = [], 0
    for where, t in _walk(doc):
        seen += 1
        conf = t.get("conf")
        label = t.get("name") or t.get("id") or where

        if conf not in VALID:
            bad.append((label, f'conf = {conf!r} is not "V" or "U"'))
            continue

        if conf == "V":
            m = t.get("measured")
            if m is None:
                bad.append((label, 'conf="V" with NO `measured` date — a value with no date is not '
                                   'a measurement'))
            elif not isinstance(m, (_dt.date, _dt.datetime)):
                bad.append((label, f'`measured` = {m!r} is not a date'))

        if conf == "U":
            owed = (t.get("owed") or "").strip()
            if not owed:
                bad.append((label, 'conf="U" with NO `owed` — an unknown with no way to settle it '
                                   'is a wish, not a record'))
    return seen, bad


def report(seen, bad) -> int:
    print("=" * 78)
    print(f"  verify_conf — {seen} tables carry a confidence tag")
    print("=" * 78)
    for label, why in bad:
        print(f"  🔴 {label}\n       {why}")
    print("-" * 78)
    if bad:
        print(f"  RESULT: RED — {len(bad)} violation(s). The schema is stated in rails.toml's "
              f"own header.")
        return 1
    print("  RESULT: GREEN — every V has a date, every U has an owed.")
    return 0


def selftest() -> int:
    import tempfile
    fixture = """
schema = 1
[[rail]]
name = "good-V"
conf = "V"
measured = 2026-07-31
[[rail]]
name = "good-U"
conf = "U"
owed = "run the thing"
[[rail]]
name = "BAD-V-no-date"
conf = "V"
[[rail]]
name = "BAD-U-no-owed"
conf = "U"
[[rail]]
name = "BAD-conf-value"
conf = "probably"
"""
    p = os.path.join(tempfile.mkdtemp(), "f.toml")
    open(p, "w", encoding="utf-8").write(fixture)
    seen, bad = check(p)
    names = {b[0] for b in bad}
    ok1 = "BAD-V-no-date" in names
    ok2 = "BAD-U-no-owed" in names
    ok3 = "BAD-conf-value" in names
    ok4 = "good-V" not in names and "good-U" not in names
    for n, v in (('conf="V" with no date -> caught', ok1),
                 ('conf="U" with no owed -> caught', ok2),
                 ('conf that is neither V nor U -> caught', ok3),
                 ('well-formed entries -> NOT flagged (no false positives)', ok4)):
        print(f"  {'OK  ' if v else 'FAIL'}  {n}")
    good = ok1 and ok2 and ok3 and ok4
    print("SELFTEST PASS — the schema in rails.toml's header is now enforced, not merely stated."
          if good else "SELFTEST FAIL — do not trust this checker.")
    return 0 if good else 1


def check_all():
    """Every .toml under ROLD, recursively. Returns (files, seen, bad_with_file)."""
    files = all_toml()
    seen_total, bad_total = 0, []
    for f in files:
        try:
            seen, bad = check(f)
        except Exception as e:                       # noqa: BLE001 — a file that will not parse is a finding
            bad_total.append((os.path.relpath(f, HERE), "<file>", f"WILL NOT PARSE: {e}"))
            continue
        seen_total += seen
        for label, why in bad:
            bad_total.append((os.path.relpath(f, HERE), label, why))
    return files, seen_total, bad_total


def report_all(files, seen, bad) -> int:
    print("=" * 78)
    print(f"  verify_conf — {len(files)} toml file(s), {seen} tables carrying a confidence tag")
    print("=" * 78)
    for f in files:
        print(f"    · {os.path.relpath(f, HERE)}")
    print("-" * 78)
    for fname, label, why in bad:
        print(f"  🔴 {fname} :: {label}\n       {why}")
    if bad:
        print("-" * 78)
        print(f"  RESULT: RED — {len(bad)} violation(s) across {len({b[0] for b in bad})} file(s).")
        return 1
    print("  RESULT: GREEN — every V has a date, every U has an owed, in every file.")
    return 0


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(selftest())
    if "--one" in sys.argv:
        sys.exit(report(*check()))
    sys.exit(report_all(*check_all()))
