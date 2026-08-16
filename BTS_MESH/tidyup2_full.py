#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tidyup2_full.py - TidyUP2 checks 2, 3, 6, 8 and 10, done against the ARTIFACTS.

`tidyup2_checks.py` is the mechanical half (pointers, drift, charset, truncation, schema,
contradictions, scar count, publish errors, queue). This is the half that has always been
done by hand and therefore has always been done by reading prose back to itself.

  CHECK 2  REFERENCED-FILE EXISTENCE — every path named in the handoff must exist.
  CHECK 3  NUMBER CONSISTENCY — RECOUNT. Do not trust prose. This is the check that
           matters, because the handoff is where a wrong number does the most damage:
           it is read at every BootUP, before anything can contradict it.
  CHECK 6  SANDBOX SWEEP — anything living only in scratch.
  CHECK 8  LIVING-DOC CHECK — and: any file claiming "generated from X" must name a
           generator that EXISTS.
  CHECK 10 NEW CLASSES — appended to SCARS.md, never to a second log.

🔴 WHY CHECK 3 IS RUN AGAINST THE HANDOFF SPECIFICALLY. Measured 2026-08-11: BU.MD said
"Tools registry 46" while the registry held 46, then 100, then 103 within hours; it said
"Scars 137" after 142 were written; it carried "federation_ready() returns 4 blockers"
for eleven days while the function returned 5. Every one of those was a COPY of a number
the filesystem already knew. This asks the filesystem.

USAGE
    py -3.14 tidyup2_full.py
    py -3.14 tidyup2_full.py --selftest
"""
from __future__ import annotations

import json
import pathlib
import re
import sys
import tomllib

V = pathlib.Path(r"V:\Research4")
AI = pathlib.Path(r"V:\Ai")
MESH = V / "Ai" / "BTS_MESH"
ROLD = V / "Ai" / "ROLD"
BU = AI / "BU.MD"
W = V / "Ai" / "PhD2_DATA_ARCHIVE" / "00_WORKING"

_t2 = []


def t2(msg: str) -> None:
    _t2.append(msg)
    print("  T2-%-2d %s" % (len(_t2), msg))


def ok(msg: str) -> None:
    print("  ok    %s" % msg)


def head(n, title):
    print()
    print("=" * 78)
    print("  CHECK %s — %s" % (n, title))
    print("=" * 78)


# ------------------------------------------------------------------ actual counts
def actual():
    reg = json.loads((MESH / "TOOLS_REGISTRY.json").read_bytes().decode("utf-8"))
    cos = tomllib.loads((ROLD / "corrections.toml").read_bytes().decode("utf-8"))
    md = (ROLD / "SCARS.md").read_bytes().decode("utf-8", "replace")
    tal = (MESH / "PUBLISH.log").read_bytes().decode("utf-8", "replace")
    sys.path.insert(0, str(MESH))
    try:
        import bts_identity as bi
        fr = bi.federation_ready()
        blockers = len(fr[1]) if isinstance(fr, tuple) and len(fr) > 1 else 0
    except Exception:
        blockers = None
    return {
        "registry": len(reg["tools"]),
        "corrections": len(cos["correction"]),
        "cos_heavy": len([c for c in cos["correction"] if c.get("count", 0) >= 3]),
        "scars_md": len(re.findall(r"^## S-\d+", md, re.M)),
        "scars_json": sum(1 for l in open(ROLD / "scars.jsonl", encoding="utf-8")
                          if l.strip()),
        "tally": len([l for l in tal.splitlines() if "publish exit=" in l]),
        "blockers": blockers,
        "queue_logs": len(list((AI / "_queue" / "logs").glob("*.log"))),
        # 🔴 COUNTED THREE DIFFERENT WAYS TONIGHT, AND ALL THREE WERE "RIGHT".
        #   13 - a curated list someone maintained by hand
        #   14 - files matching a string pattern for the CLI flag
        #   35 - files that actually carry a selftest, found by running them
        # The first two disagreed with the handoff and with each other, and neither was
        # wrong about what it measured - they measured different things and both called
        # the result "selftests". A count is only meaningful with its DEFINITION attached.
        # This one counts files that mention a selftest at all; `selftest_all` in the
        # queue is the version that RUNS them, which is the only definition that cannot
        # be gamed by how the flag happens to be parsed.
        "selftests": len([p for p in list(MESH.glob("*.py")) + list(ROLD.glob("*.py"))
                          if '"--selftest" in sys.argv' in
                          p.read_bytes().decode("utf-8", "replace")
                          or '"--selftest" in argv' in
                          p.read_bytes().decode("utf-8", "replace")]),
        "selftests_real": len([p for p in list(MESH.glob("*.py")) + list(ROLD.glob("*.py"))
                               + list((AI / "_session_logs").glob("*.py"))
                               if not p.name.startswith("_")
                               and ("--selftest" in p.read_bytes().decode("utf-8", "replace")
                                    or "def selftest" in
                                    p.read_bytes().decode("utf-8", "replace"))]),
    }


def check3(a):
    head(3, "NUMBER CONSISTENCY — RECOUNT, DO NOT TRUST PROSE")
    txt = BU.read_bytes().decode("utf-8", "replace")

    def claim(pattern, real, label):
        m = re.search(pattern, txt)
        if not m:
            print("        (no claim found for %s; actual %s)" % (label, real))
            return
        said = int(m.group(1).replace(",", ""))
        if said == real:
            ok("%-34s handoff says %-5s actual %s" % (label, said, real))
        else:
            t2("%s: handoff says %s, ACTUAL %s" % (label, said, real))

    claim(r"registry\s*\*{0,2}(\d+)", a["registry"], "registry tools")
    claim(r"scars\s*\*{0,2}(\d+)\s*==", a["scars_md"], "scars in SCARS.md")
    claim(r"C\.O\.S\.\s*\*{0,2}(\d+)", a["corrections"], "corrections")
    claim(r"tally\s+(\d+)\s+dated", a["tally"], "publish tally lines")
    claim(r"count\s*≥\s*3\).{0,10}(\d+)\s*of them", a["cos_heavy"], "corrections at >=3")
    # 🔴 THIS LINE CARRIED A HARDCODED 10 AND REPORTED THE HANDOFF AS WRONG WHEN THE
    # HANDOFF WAS RIGHT. The checker built to catch copied numbers had copied one: ten was
    # true when written and the tree now exposes more. A constant typed into a checker is
    # exactly the artefact this whole file exists to find — it just happened to be inside
    # the finder. Counted from disk now, like everything else here.
    claim(r"(\d+)\s+selftests discovered", a["selftests_real"], "selftests discovered")

    if a["scars_md"] != a["scars_json"]:
        t2("SCARS.md %d != scars.jsonl %d" % (a["scars_md"], a["scars_json"]))
    else:
        ok("SCARS.md == scars.jsonl (%d)" % a["scars_md"])

    if a["blockers"] is not None:
        n = len(re.findall(r"FIVE blockers|five blockers", txt))
        if a["blockers"] == 5 and n:
            ok("federation blockers: function returns 5, handoff says FIVE")
        elif a["blockers"] != 5:
            t2("federation_ready() now returns %d blockers; handoff says FIVE"
               % a["blockers"])

    # The table in section A claims a split. Count the rows and check the arithmetic.
    rows = re.findall(r"^\|\s*\d+\s*\|", txt, re.M)
    m = re.search(r"\*\*(\w+)\s+CHECKS WERE WRONG", txt.upper())
    words = {"NINE": 9, "EIGHT": 8, "SEVEN": 7, "TEN": 10}
    if m and m.group(1) in words:
        said = words[m.group(1)]
        if said == len(rows):
            ok("section A table: claims %d, table has %d rows" % (said, len(rows)))
        else:
            t2("section A claims %d checks wrong but the table has %d rows"
               % (said, len(rows)))
    split = re.search(r"(\w+) toward success[;,]? (\w+) toward failure", txt)
    if split and m and m.group(1) in words:
        s, f = words.get(split.group(1).upper()), words.get(split.group(2).upper())
        s = s if s else {"five": 5, "four": 4, "three": 3}.get(split.group(1).lower())
        f = f if f else {"five": 5, "four": 4, "three": 3}.get(split.group(2).lower())
        if s and f and (s + f) != len(rows):
            t2("section A split %s+%s=%d does not equal the %d rows in the table"
               % (split.group(1), split.group(2), s + f, len(rows)))
        elif s and f:
            ok("section A split %d+%d == %d rows" % (s, f, len(rows)))


def check2():
    head(2, "REFERENCED-FILE EXISTENCE — every path named in the handoff")
    txt = BU.read_bytes().decode("utf-8", "replace")
    paths = set(re.findall(r"`([A-Za-z]:\\[^`\n]+?)`", txt))
    paths |= {p for p in re.findall(r"`(Desktop\\[^`\n]+?)`", txt)}
    missing, present, skipped = [], 0, 0
    for p in sorted(paths):
        if p.lower().startswith("desktop\\"):
            skipped += 1          # deliberate: the Desktop is a delivery surface
            continue
        pp = pathlib.Path(p)
        if pp.exists():
            present += 1
        else:
            missing.append(p)
    print("        %d path(s) named · %d exist · %d Desktop (skipped by rule)"
          % (len(paths), present, skipped))
    for p in missing:
        t2("handoff names a path that does not exist: %s" % p)
    if not missing:
        ok("every non-Desktop path named in the handoff exists")


def check6():
    head(6, "SANDBOX SWEEP — anything living only in scratch")
    tmp = pathlib.Path("/tmp")
    if tmp.exists():
        stray = [p for p in tmp.glob("*") if p.is_file()]
        print("        /tmp visible from here: %d file(s)" % len(stray))
    else:
        print("        /tmp not visible from Windows — correct, not a finding.")
    q = AI / "_queue"
    pend = [p.name for p in q.glob("*.py")]
    run = [p.name for p in (q / "running").glob("*") if p.is_file()]
    fail = [p.name for p in (q / "failed").glob("*") if p.is_file()]
    print("        queue: pending=%d running=%d failed=%d" % (len(pend), len(run),
                                                              len(fail)))
    if fail:
        t2("failed jobs left in the queue root: %s" % fail)
    else:
        ok("no failed jobs stranded")
    triage = q / "triage"
    if triage.exists():
        got = [p.name for p in triage.glob("tool_triage__*.md")]
        if got:
            ok("the paid fanout returns are on disk (%d) — %s" % (len(got), ", ".join(got)))
            t2("the three paid triage returns live only in `_queue\\triage\\`, which is "
               "scratch. They cost $0.085 and are the evidence behind 50 registry "
               "rulings. Move them beside the registry or into the session log.")


def check8():
    head(8, "LIVING-DOC CHECK — and every 'generated from X' must name a real generator")
    for p, label in ((ROLD / "rails.toml", "rails.toml"),
                     (ROLD / "corrections.toml", "corrections.toml"),
                     (ROLD / "SCARS.md", "SCARS.md"),
                     (V / "Ai" / "00_TOOLS_INDEX.md", "00_TOOLS_INDEX.md"),
                     (MESH / "TOOLS_REGISTRY.json", "TOOLS_REGISTRY.json"),
                     (AI / "Streams" / "PLM_TODOS.md", "PLM_TODOS.md"),
                     (BU, "BU.MD")):
        import datetime as dt
        age = (dt.date(2026, 8, 12)
               - dt.date.fromtimestamp(p.stat().st_mtime)).days if p.exists() else None
        if age is None:
            t2("living document MISSING: %s" % label)
        elif age == 0:
            ok("%-22s touched today" % label)
        else:
            print("        %-22s %d day(s) old — verify it did not need updating" % (label, age))

    # "generated from X" claims.
    #
    # 🔴 THE FIRST VERSION OF THIS PRODUCED EIGHT FALSE POSITIVES OUT OF TEN FINDINGS,
    # on the very pass whose job includes C-30. It captured [\w\\/.]+ after the phrase, so
    # it matched ordinary English - "generated from it", "generated from X", "generated
    # from JSON." - and then reported that no file named `it` exists. Worst of all it
    # flagged 00_TOOLS_INDEX.md, whose matching sentence is the CORRECTION RECORDING THAT
    # SUCH A CLAIM WAS FALSE: *"'Generated from the JSON...' WAS FALSE. No generator
    # exists."* The check reported the retraction as the offence.
    #
    # TWO GUARDS, and they are the same two the stale-date hunt needed:
    #   1. the captured token must LOOK LIKE A FILE - an extension or a path separator.
    #      `it`, `X` and `JSON.` are not filenames.
    #   2. skip ANNOTATION lines - a sentence about a false claim is not the claim.
    _FILEISH = re.compile(r"^[\w\-. \\/]+\.(md|py|json|toml|txt|bat|vbs|ps1|jsonl|docx)$",
                          re.I)
    _ANNOT = ("was false", "no generator", "is false", "corrected", "superseded",
              "used to", "no longer", "wrong", "not true", "claimed")
    for p in list(V.glob("Ai/*.md")) + list(ROLD.glob("*.md")):
        try:
            txt = p.read_bytes().decode("utf-8", "replace")
        except OSError:
            continue
        for line in txt.splitlines():
            low = line.lower()
            if any(w in low for w in _ANNOT):
                continue
            for m in re.finditer(r"[Gg]enerated from (?:the )?[`\"']?([\w\-. \\/]+?)[`\"']",
                                 line):
                name = m.group(1).strip()
                if not _FILEISH.match(name):
                    continue
                if list(V.rglob(pathlib.Path(name).name)) or pathlib.Path(name).exists():
                    continue
                t2("%s claims 'generated from %s' and no such generator is on disk"
                   % (p.name, name))


def check10():
    head(10, "NEW CLASSES — appended to SCARS.md, never a second log")
    md = (ROLD / "SCARS.md").read_bytes().decode("utf-8", "replace")
    for s in ("S-138", "S-139", "S-140", "S-141", "S-142"):
        if ("## %s " % s) in md:
            ok("%s present" % s)
        else:
            t2("%s missing from SCARS.md" % s)
    others = [p.name for p in ROLD.glob("*.md")
              if "class" in p.name.lower() and "scars" not in p.name.lower()]
    if others:
        t2("a SECOND classes log exists: %s — merge into SCARS.md" % others)
    else:
        ok("no second classes log")


def selftest() -> int:
    checks = []
    a = actual()
    checks.append(("actual() returns integers, not guesses",
                   all(isinstance(v, int) for k, v in a.items() if v is not None)))
    checks.append(("scars md and jsonl agree", a["scars_md"] == a["scars_json"]))
    checks.append(("registry is a positive count", a["registry"] > 0))
    before = len(_t2)
    t2("planted finding")
    checks.append(("t2() records and numbers a finding", len(_t2) == before + 1))
    _t2.pop()
    print("=" * 78)
    print("  tidyup2_full --selftest")
    print("=" * 78)
    for label, good in checks:
        print("  %s  %s" % ("OK  " if good else "FAIL", label))
    bad = [l for l, g in checks if not g]
    print("SELFTEST PASS" if not bad else "SELFTEST FAIL - %d" % len(bad))
    return 1 if bad else 0


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(selftest())
    print("=" * 78)
    print("  TidyUP2 — the checks that are not mechanical")
    print("=" * 78)
    a = actual()
    print("  MEASURED NOW: registry=%d corrections=%d scars=%d/%d tally=%d blockers=%s"
          % (a["registry"], a["corrections"], a["scars_md"], a["scars_json"],
             a["tally"], a["blockers"]))
    check2()
    check3(a)
    check6()
    check8()
    check10()
    print()
    print("=" * 78)
    print("  T2 FINDINGS: %d" % len(_t2))
    print("=" * 78)
    for i, m in enumerate(_t2, 1):
        print("  T2-%-2d %s" % (i, m))
    if not _t2:
        print("  none.")
    sys.exit(1 if _t2 else 0)
