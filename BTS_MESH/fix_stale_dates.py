#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""fix_stale_dates.py - retire a superseded constant from the LIVE tree. Cowork, 2026-08-11.

THE PROBLEM THIS EXISTS FOR
---------------------------
`00_ROLD_COMMANDS_TidyUp_BootUp.md` line 589, written 2026-08-06:

    "Verified fixed: zero live `2026-10-10` references remain."

**Twenty-two live references remained.** The Vertex credit expiry had two versions - an
unsourced 2026-10-10 and a MEASURED 2026-10-13 (the console banner read 74 days remaining
on 2026-07-31; 07-31 + 74 = 10-13 exactly). The 08-06 sweep looked at three documents it
already suspected, so it could only confirm what it already believed.

  ==> SCOPING A HUNT TO THE DOCUMENTS YOU SUSPECT IS NOT A HUNT.

WHY THIS IS A TOOL AND NOT A find-and-replace
---------------------------------------------
A blind replace would destroy the RECORD OF THE CORRECTION. The tree contains three
different kinds of line carrying the old date, and only one of them is a defect:

  ASSERTION  "the $300 credit EXPIRES 2026-10-10"                    <- fix this
  ANNOTATION "The old note said the credit expires ~2026-10-10"      <- LEAVE IT
  ARCHIVE    a dated session record, or SCARS.md                     <- NEVER TOUCH

Rewriting an annotation turns "we got this wrong and here is how we found out" into a
sentence that says nothing. Rewriting an archive record falsifies history. The whole
value of this repo's scar discipline is that the wrong answers are still legible.

REFUSALS
  * .py files are re-parsed with ast after the edit; a file that would not compile is
    RESTORED and reported. Verifying content is not verifying that it still runs.
  * a file whose byte count on read != stat is skipped (the mount's truncation signature)
  * --dry-run is THE DEFAULT. Nothing is written without --apply.
  * every touched file is backed up next to itself before the write

USAGE
    py -3.14 fix_stale_dates.py                 # dry run: show every hit and its verdict
    py -3.14 fix_stale_dates.py --apply         # write
    py -3.14 fix_stale_dates.py --selftest      # negative controls
"""
from __future__ import annotations

import ast
import pathlib
import shutil
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from tidyup2_checks import (CONTRADICTION_STALE, CONTRADICTION_EXPECT,  # noqa: E402
                            _is_archive, _is_annotation, _TEXTY)

V_RESEARCH = pathlib.Path(r"V:\Research4")
V_AI = pathlib.Path(r"V:\Ai")
ROOTS = [V_RESEARCH / "Ai", V_AI / "Streams", V_RESEARCH / "CLAUDE.md", V_AI / "BU.MD"]

# The published subtree holds FROZEN SNAPSHOTS of control documents (00_TOOLS_INDEX.md,
# TOOLS_REGISTRY.json, ...) taken 2026-08-01. Those are duplicates and the answer to a
# duplicate is not to edit it - it is to remove it. Handled separately; skipped here so
# this tool does not quietly make a stale copy look current, which is worse than leaving
# it obviously stale.
SKIP_DIRS = ("\\phd2_data_archive\\00_working\\",)

NOTE = ("2026-10-13 (MEASURED: console banner read 74 days remaining on 2026-07-31)")


def _skipped(p: pathlib.Path) -> bool:
    return any(s in str(p).lower() for s in SKIP_DIRS)


def scan():
    """Return (assertions, annotations, skipped). Reads only."""
    assertions, annotations, skipped = [], [], []
    seen = set()
    for root in ROOTS:
        files = [root] if root.is_file() else sorted(root.rglob("*"))
        for p in files:
            if not p.is_file() or p.suffix.lower() not in _TEXTY or p in seen:
                continue
            seen.add(p)
            if _is_archive(p):
                continue
            if p.resolve() == pathlib.Path(__file__).resolve():
                continue
            try:
                data = p.read_bytes()
            except OSError:
                continue
            if len(data) != p.stat().st_size:
                skipped.append((p, "short read - truncation signature"))
                continue
            text = data.decode("utf-8", errors="replace")
            if CONTRADICTION_STALE not in text:
                continue
            if _skipped(p):
                skipped.append((p, "frozen snapshot in the published subtree - "
                                   "the answer to a duplicate is removal, not an edit"))
                continue
            for i, line in enumerate(text.splitlines(), 1):
                if CONTRADICTION_STALE not in line:
                    continue
                (annotations if _is_annotation(line) else assertions).append(
                    (p, i, line.rstrip()))
    return assertions, annotations, skipped


def apply(assertions) -> tuple:
    """Rewrite ONLY the asserting lines. Returns (written, refused)."""
    by_file = {}
    for p, i, _ in assertions:
        by_file.setdefault(p, set()).add(i)
    written, refused = [], []
    for p, lines in sorted(by_file.items()):
        original = p.read_bytes().decode("utf-8", errors="replace")
        out, changed = [], 0
        for i, line in enumerate(original.splitlines(keepends=True), 1):
            if i in lines and CONTRADICTION_STALE in line:
                out.append(line.replace(CONTRADICTION_STALE, CONTRADICTION_EXPECT))
                changed += 1
            else:
                out.append(line)
        new = "".join(out)
        if p.suffix.lower() == ".py":
            try:
                ast.parse(new)
            except SyntaxError as e:
                refused.append((p, "would not parse after the edit: %s" % e))
                continue
        bak = p.with_suffix(p.suffix + ".stale-date.2026-08-11.bak")
        shutil.copy2(p, bak)
        p.write_text(new, encoding="utf-8")
        # ASSERT THE ARTIFACT: read it back and count.
        back = p.read_bytes().decode("utf-8", errors="replace")
        still = sum(1 for ln in back.splitlines()
                    if CONTRADICTION_STALE in ln and not _is_annotation(ln))
        written.append((p, changed, still))
    return written, refused


def selftest() -> int:
    import tempfile
    checks = []
    with tempfile.TemporaryDirectory() as d:
        dd = pathlib.Path(d)
        # an ASSERTION in python is rewritten and the file still parses
        a = dd / "a.py"
        a.write_text('X = "credit EXPIRES %s unspent"\n' % CONTRADICTION_STALE,
                     encoding="utf-8")
        w, r = apply([(a, 1, "")])
        got = a.read_text(encoding="utf-8")
        checks.append(("an assertion is rewritten",
                       CONTRADICTION_EXPECT in got and CONTRADICTION_STALE not in got))
        checks.append(("the rewritten .py still parses", not r))

        # a file that WOULD break is refused and left alone
        b = dd / "b.py"
        src = 'X = "%s"\ndef f(:\n' % CONTRADICTION_STALE      # already broken on purpose
        b.write_text(src, encoding="utf-8")
        w2, r2 = apply([(b, 1, "")])
        checks.append(("a .py that would not parse is REFUSED, not written",
                       bool(r2) and b.read_text(encoding="utf-8") == src))

        # an ANNOTATION is never selected in the first place
        checks.append(("an annotation is not an assertion",
                       _is_annotation("the old note said it expires ~%s"
                                      % CONTRADICTION_STALE)))
        checks.append(("a backticked mention is not an assertion",
                       _is_annotation("zero live `%s` references remain"
                                      % CONTRADICTION_STALE)))
        checks.append(("a bare claim IS an assertion",
                       not _is_annotation("the credit expires %s"
                                          % CONTRADICTION_STALE)))
    print("=" * 78)
    print("  fix_stale_dates --selftest")
    print("=" * 78)
    for label, good in checks:
        print("  %s  %s" % ("OK  " if good else "FAIL", label))
    bad = [l for l, g in checks if not g]
    print("SELFTEST PASS - it rewrites claims, refuses to break code, and leaves the "
          "record of the correction intact." if not bad
          else "SELFTEST FAIL - %d check(s)." % len(bad))
    return 1 if bad else 0


def main() -> int:
    if "--selftest" in sys.argv:
        return selftest()
    assertions, annotations, skipped = scan()
    print("=" * 78)
    print("  fix_stale_dates   %s -> %s" % (CONTRADICTION_STALE, CONTRADICTION_EXPECT))
    print("=" * 78)
    print("  ASSERTIONS (defects, will be rewritten): %d" % len(assertions))
    for p, i, line in assertions:
        print("    %s:%d" % (str(p).replace(str(V_RESEARCH) + "\\", ""), i))
        print("        %s" % line.strip()[:110])
    print()
    print("  ANNOTATIONS (the record of the correction - LEFT ALONE): %d" % len(annotations))
    for p, i, _ in annotations:
        print("    %s:%d" % (str(p).replace(str(V_RESEARCH) + "\\", ""), i))
    print()
    print("  SKIPPED: %d" % len(skipped))
    for p, why in skipped:
        print("    %s\n        %s" % (str(p).replace(str(V_RESEARCH) + "\\", ""), why))

    if "--apply" not in sys.argv:
        print()
        print("  DRY RUN. Nothing written. Re-run with --apply.")
        return 0

    written, refused = apply(assertions)
    print()
    print("=" * 78)
    print("  APPLIED - each file read back from disk and re-counted")
    print("=" * 78)
    for p, changed, still in written:
        flag = "" if still == 0 else "   <== %d ASSERTION(S) REMAIN" % still
        print("  %-58s %2d line(s)%s"
              % (str(p).replace(str(V_RESEARCH) + "\\", ""), changed, flag))
    for p, why in refused:
        print("  REFUSED  %s\n           %s" % (p, why))
    bad = [1 for _, _, still in written if still] + [1 for _ in refused]
    print("  RESULT:", "GREEN" if not bad else "RED")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
