#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tidyup2_checks.py - TidyUP2, the ADVERSARIAL pass, as a PROGRAM. Cowork, 2026-08-11.

TidyUP asks "did I do the steps." TidyUP2 asks "what did doing them break, and what did
I claim without checking."

WHY THIS FILE EXISTS
--------------------
TidyUP2 ran on 2026-08-11 as a .bat with six checks written as `py -3.14 -c "..."`, and
THREE of them returned garbage that read as success:

  * check 6, the contradiction hunt, printed `BU.MD: []  CLAUDE.md: []  rails.toml: []`.
    CLAUDE.md unambiguously contains 2026-10-13. cmd had eaten the regex. A check that
    reports "no problems found" because its own pattern was mangled is not a weak check,
    it is a FALSE GREEN, which is worse than no check at all.
  * check 5, the C.O.S. schema check, compared every entry against "whichever entry
    happens to have the most keys" and therefore flagged all 29 as odd. 29 of 29 findings
    is noise, and the noise HID the one real fault: C-29 shipped with `detail` where the
    other 28 use `rule`, and corrections.py renders c.get("rule", "") - so the newest
    correction in the C.O.S. printed its heading and then nothing at all.
  * check 2 was a separate .py sitting in the queue root, where the runner claimed it as a
    job and moved it out from under the bat that was calling it.

That is C-06 - "never inline a program in a shell" - violated on the same day the document
quoting C-06 was written. The defect was never the escape character. It was inlining a
program into a shell with its own opinions about punctuation.

ASCII ONLY ON STDOUT. Not "no emoji in a .bat" - the general rule. Measured 2026-08-11:
four monitors died with UnicodeEncodeError the moment a scheduler redirected them, and an
em dash in a selftest came back as mojibake in the queue log the same night (S-134).

USAGE
    py -3.14 tidyup2_checks.py              # run every check, exit non-zero on RED
    py -3.14 tidyup2_checks.py --selftest   # negative controls: prove the checks can FIRE
"""
from __future__ import annotations

import json
import pathlib
import re
import subprocess
import sys
import tempfile
import tomllib

V_RESEARCH = pathlib.Path(r"V:\Research4")
V_AI = pathlib.Path(r"V:\Ai")
ROLD = V_RESEARCH / "Ai" / "ROLD"
MESH = V_RESEARCH / "Ai" / "BTS_MESH"
SESS = V_AI / "_session_logs"
WORKING = V_RESEARCH / "Ai" / "PhD2_DATA_ARCHIVE" / "00_WORKING"

CONTROL_DOCS = [V_AI / "BU.MD",
                V_RESEARCH / "CLAUDE.md",
                ROLD / "SCARS.md",
                ROLD / "corrections.toml",
                V_RESEARCH / "Ai" / "00_TOOLS_INDEX.md"]

# The C.O.S. schema, DECLARED. Not inferred from whichever entry is fattest.
# `rule` is what corrections.py line 121 actually renders; an entry without it prints EMPTY.
COS_REQUIRED = {"id", "short", "rule", "count", "first", "last", "status",
                "mechanism", "occurrences"}
COS_OPTIONAL_PREFIXES = ("_note",)          # dated marginalia, deliberate
COS_OPTIONAL = {"detail"}

# The contradiction class this hunt exists for: the Vertex credit expiry. rails.toml carries
# the MEASURED date (console banner said 74 days remaining on 2026-07-31 -> 2026-10-13).
# Any 2026-10-10 anywhere is the unsourced figure that was superseded.
CONTRADICTION_PATTERN = r"2026-10-\d\d"
CONTRADICTION_EXPECT = "2026-10-13"
CONTRADICTION_STALE = "2026-10-10"

_reds: list = []
_notes: list = []


def red(msg: str) -> None:
    _reds.append(msg)
    print("  RED   " + msg)


def ok(msg: str) -> None:
    print("  ok    " + msg)


def note(msg: str) -> None:
    _notes.append(msg)
    print("        " + msg)


def _age(p: pathlib.Path) -> str:
    import datetime as _d
    ts = _d.datetime.fromtimestamp(p.stat().st_mtime)
    return ts.strftime("%Y-%m-%d %H:%M")


def head(n: int, title: str) -> None:
    print()
    print("=" * 78)
    print("  %d. %s" % (n, title))
    print("=" * 78)


# --------------------------------------------------------------------------------------
def check_pointers() -> None:
    head(1, "POINTER RESOLUTION - every operator line in every control document")
    r = subprocess.run(["py", "-3.14", str(ROLD / "verify_pointers.py")],
                       capture_output=True, text=True, errors="replace")
    for line in (r.stdout or "").splitlines():
        if line.strip().startswith(("FAIL", "ANCHOR", "OPCODE", "resolved=", "RESULT:")) \
                or "resolved=" in line or "RESULT:" in line:
            print("        " + line.strip())
    if r.returncode == 0:
        ok("verify_pointers GREEN")
    else:
        red("verify_pointers exited %s" % r.returncode)


def check_tool_drift() -> None:
    head(2, "TOOL DRIFT - a .py in the tree that is in NEITHER index")
    note("both files are hand-maintained, no generator exists, and they have drifted in")
    note("BOTH directions (bts_identity 07-15; bts_tools 07-28)")
    reg_path = MESH / "TOOLS_REGISTRY.json"
    idx_path = V_RESEARCH / "Ai" / "00_TOOLS_INDEX.md"
    try:
        tools = json.loads(reg_path.read_text(encoding="utf-8"))["tools"]
    except Exception as e:
        red("TOOLS_REGISTRY.json unreadable: %s" % e)
        return
    reg_blob = json.dumps(tools).lower()
    idx_blob = idx_path.read_text(encoding="utf-8", errors="replace").lower()
    note("registry entries %d | index bytes %s" % (len(tools), format(len(idx_blob), ",")))

    both, only_idx, only_reg = [], [], []
    for root in (MESH, ROLD, SESS):
        if not root.is_dir():
            red("root MISSING (not empty - missing): %s" % root)
            continue
        for p in sorted(root.glob("*.py")):
            if p.name.startswith("_"):
                continue
            stem = p.stem.lower()
            in_reg, in_idx = stem in reg_blob, stem in idx_blob
            if not in_reg and not in_idx:
                both.append(p)
            elif not in_reg:
                only_idx.append(p)
            elif not in_idx:
                only_reg.append(p)
    for p in both:
        red("in NEITHER index: %s" % p)
    for p in only_reg:
        note("in registry, not on the index page: %s" % p.name)
    for p in only_idx:
        note("on the index page, not in the registry: %s" % p.name)
    if not both:
        ok("no tool is invisible to both indexes")

    bad = [t.get("id") for t in tools
           if (t.get("conf") == "V" and not t.get("measured"))
           or (t.get("conf") == "U" and not t.get("owed"))]
    if bad:
        red("registry conf-schema violations: %s" % bad)
    else:
        ok("registry conf schema clean (V carries measured, U carries owed)")


def _high_chars(text: str):
    out = []
    for i, line in enumerate(text.splitlines(), 1):
        if any(ord(c) > 0x2500 for c in line):
            out.append(i)
    return out


def check_bat_charset(extra_roots=None) -> None:
    head(3, "HIGH CHARACTERS IN A .bat - cmd mangles the line and the option vanishes")
    roots = list(extra_roots or []) + [V_AI / "_queue",
                                       pathlib.Path(r"C:\Users\Papa\OneDrive\Desktop")]
    hits = []
    for root in roots:
        if not root.exists():
            continue
        for p in sorted(root.rglob("*.bat")):
            for n in _high_chars(p.read_text(encoding="utf-8", errors="replace")):
                hits.append((p, n))
    for p, n in hits[:20]:
        red("high chars in %s line %d" % (p, n))
    if not hits:
        ok("no .bat carries characters cmd cannot render")


def check_truncation() -> None:
    head(4, "TRUNCATION CONTROL - stat bytes vs bytes READ, never chars")
    note("the mount's silent short-read signature; measured 13 times")
    for p in CONTROL_DOCS:
        if not p.exists():
            red("control document MISSING: %s" % p)
            continue
        st, rd = p.stat().st_size, len(p.read_bytes())
        line = "%-24s stat=%9s  read=%9s" % (p.name, format(st, ","), format(rd, ","))
        if st == rd:
            ok(line)
        else:
            red(line + "  MISMATCH")


def check_cos_schema(path: pathlib.Path = None) -> None:
    head(5, "C.O.S. SCHEMA CONFORMITY - an entry the printer cannot read")
    note("declared schema, not 'whichever entry has the most keys' - that comparison")
    note("reported 29 of 29 as odd and hid the one entry that was really broken")
    path = path or (ROLD / "corrections.toml")
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        red("corrections.toml DOES NOT PARSE: %s" % e)
        red("the entire carry-over system is silently off when this happens (S-118)")
        return
    entries = data.get("correction", [])
    note("entries %d" % len(entries))
    clean = True
    for e in entries:
        keys = set(e)
        missing = COS_REQUIRED - keys
        if missing:
            clean = False
            red("%s is MISSING %s -- corrections.py renders c.get('rule'), so an entry "
                "without it prints its heading and NOTHING" % (e.get("id", "?"),
                                                               sorted(missing)))
        extra = {k for k in keys - COS_REQUIRED - COS_OPTIONAL
                 if not k.startswith(COS_OPTIONAL_PREFIXES)}
        if extra:
            note("%s carries extra keys %s (allowed, reported for visibility)"
                 % (e.get("id", "?"), sorted(extra)))
    counted = [e for e in entries
               if isinstance(e.get("occurrences"), list)
               and len(e["occurrences"]) != e.get("count")]
    for e in counted:
        clean = False
        red("%s count=%s but %d occurrences are evidenced -- a count must never be "
            "asserted without proof" % (e.get("id"), e.get("count"),
                                        len(e["occurrences"])))
    if clean:
        ok("every entry carries the keys the printer needs, and every count is evidenced")


def _hunt(paths) -> dict:
    return {p.name: sorted(set(re.findall(CONTRADICTION_PATTERN,
                                          p.read_text(encoding="utf-8", errors="replace"))))
            for p in paths if p.exists()}


# ARCHIVE-class. Read-only, never consulted for state, and it is SUPPOSED to contain the old
# figure - that is what an archive is for. Flagging it would paint the tree permanently RED,
# and a check that cries wolf gets muted (the Desktop-refusal reasoning, applied to history).
_ARCHIVE_MARKERS = ("00_next_session_handoff", "\\archive\\", "\\returns_", "queue.json",
                    "00_rold_commands_tidyup_bootup", "_delme", "\\.git\\", "\\dupes\\",
                    "\\_session_logs\\", "\\_transcripts\\", "\\wargame\\")
# A DATED SESSION RECORD IS ARCHIVE BY CONSTRUCTION. Files named 2026-07-13_9ea30d54_*.md
# are what a session BELIEVED on that date. Editing them would be falsifying a record, and
# flagging them forever would drown the four findings that are actually actionable - the
# same reasoning that already exempts the Desktop and SCARS.md.
# The trailing [a-z]? matters: `ch4_review_2026-07-13b` is a dated record and the suffix
# letter is a revision marker, not part of a different name.
_DATED_RECORD = re.compile(r"^\d{4}-\d{2}-\d{2}[_-]|[_-]\d{4}-\d{2}-\d{2}[a-z]?$")

# 🔴 A TOOL WHOSE SUBJECT IS THE STALE CONSTANT WILL ALWAYS CONTAIN IT.
# These three exist to find, explain and retire 2026-10-10. Their docstrings and comments
# quote it by necessity - "the 2026-10-10 credit date that four live documents still
# asserted" is a description of the defect, and rewriting it to 2026-10-13 produces a
# sentence that is simply false. Flagging them forever would also guarantee this check can
# never close green, and a check that cannot close green gets muted.
# Same reasoning as the SCARS.md and Desktop exemptions: the record of a correction is not
# an instance of the thing being corrected.
SELF_REFERENTIAL = frozenset({"tidyup2_checks.py", "fix_stale_dates.py", "maint_sweep.py"})
# A line that WARNS about the stale figure is not an assertion of it. "Any 2026-10-10 you see
# is stale" is the fix working, not the defect. Distinguishing these is the difference between
# 4 actionable findings and 20 lines nobody reads.
# Widened 2026-08-11 after fix_stale_dates' selftest REFUSED to run against the narrower
# list. The real annotations in this tree are REPORTED SPEECH - "the old note said the
# credit expires ~2026-10-10", "It said ... on billing account 0142FE, which NEVER HELD A
# CREDIT" - and none of those words were in the original list. A rewriter running against
# it would have turned each correction into a sentence that asserts the thing it exists to
# retract. The selftest catching that is the only reason it did not happen.
_ANNOTATION_MARKERS = ("stale", "superseded", "unsourced", "typographical", "was ",
                       "no longer", "corrected", "incorrect", "false",
                       "rewritten", "old note", "said", "previously", "used to",
                       "no such", "never held", "retired", "replaced")
_TEXTY = {".md", ".py", ".toml", ".json", ".txt", ".jsonl"}


def _is_archive(p: pathlib.Path) -> bool:
    s = str(p).lower()
    # A DATED PARENT DIRECTORY MAKES ITS CONTENTS DATED. `ch4_review_2026-07-13b\
    # REVIEW_SYNTHESIS.md` is a July 13 record; the file's own name says nothing, and
    # checking only the filename left exactly one hit that could never be cleared -
    # which would have held this check permanently RED over a document that is supposed
    # to preserve what was believed that day.
    return (any(m in s for m in _ARCHIVE_MARKERS)
            or bool(_DATED_RECORD.search(p.stem))
            or any(_DATED_RECORD.search(parent.name) for parent in p.parents)
            or p.name in SELF_REFERENTIAL)


def _is_annotation(line: str) -> bool:
    """Is this line TALKING ABOUT the stale figure rather than ASSERTING it?

    Three signals, and the second one is the one that caught this check out. BU.MD's own
    new text quotes the false 2026-08-06 claim - *"Verified fixed: zero live `2026-10-10`
    references remain"* - in order to record that it was wrong. Flagging that as an
    assertion would mean the write-up of the defect becomes the defect.

      1. an explicit marker word (stale, superseded, unsourced, corrected, false, ...)
      2. THE DATE IS IN BACKTICKS - a date in code-quotes is being discussed, not claimed
      3. the line is a blockquote, i.e. it is quoting someone or something else
    """
    low = line.lower()
    if any(m in low for m in _ANNOTATION_MARKERS) or CONTRADICTION_EXPECT in line:
        return True
    # The date inside ANY quoting mark is being discussed, not claimed. Backticks in
    # Markdown, double quotes in a Python comment quoting an older comment.
    for open_q, close_q in (("`", "`"), ('"', '"'), ("'", "'")):
        if "%s%s%s" % (open_q, CONTRADICTION_STALE, close_q) in line:
            return True
    # A quoted CLAUSE containing the date - '"expires ~2026-10-10"' - is reported speech.
    if '"' in line and CONTRADICTION_STALE in line:
        head, _, tail = line.partition('"')
        if CONTRADICTION_STALE in tail and '"' in tail:
            return True
    return line.lstrip().startswith(">")


def hunt_live_assertions():
    """Walk the LIVE tree and split hits into ASSERTIONS and ANNOTATIONS.

    The .bat version looked at three files. The stale figure was in FOUR OTHERS at the time,
    including 00_TOOLS_INDEX.md - the page BootUP! is told to read before writing any script -
    and TOOLS_REGISTRY.json. Scoping a hunt to the documents you already suspect is how a
    document five days earlier could record "Verified fixed: zero live 2026-10-10 references
    remain" while four live references sat in the tree. (C-29.)
    """
    roots = [V_RESEARCH / "Ai", V_AI / "Streams", V_RESEARCH / "CLAUDE.md", V_AI / "BU.MD"]
    assertions, annotations = [], []
    seen = set()
    for root in roots:
        files = [root] if root.is_file() else sorted(root.rglob("*"))
        for p in files:
            if not p.is_file() or p.suffix.lower() not in _TEXTY or _is_archive(p):
                continue
            if p.resolve() == pathlib.Path(__file__).resolve():
                continue                       # the checker's own constant is not a finding
            if p in seen:
                continue
            seen.add(p)
            try:
                text = p.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            if CONTRADICTION_STALE not in text:
                continue
            for i, line in enumerate(text.splitlines(), 1):
                if CONTRADICTION_STALE not in line:
                    continue
                if _is_annotation(line):
                    annotations.append((p, i))
                else:
                    assertions.append((p, i, line.strip()[:110]))
    return assertions, annotations


def check_contradictions() -> None:
    head(6, "CONTRADICTION HUNT - the 10-10 vs 10-13 class")
    note("expect %s only. %s asserted anywhere LIVE is the unsourced figure."
         % (CONTRADICTION_EXPECT, CONTRADICTION_STALE))

    # NEGATIVE CONTROL FIRST. This is the whole reason this check is a .py.
    # The .bat version returned [] for every file and that was indistinguishable from
    # "clean". A hunt that cannot be shown to FIND anything is decoration.
    with tempfile.TemporaryDirectory() as d:
        plant = pathlib.Path(d) / "PLANTED.md"
        plant.write_text("the credit expires %s, which is stale\n" % CONTRADICTION_STALE,
                         encoding="utf-8")
        if _hunt([plant]).get("PLANTED.md") != [CONTRADICTION_STALE]:
            red("NEGATIVE CONTROL FAILED - the hunt did not find a planted %s. "
                "Every result below is meaningless." % CONTRADICTION_STALE)
            return
        ok("negative control: the hunt finds a planted %s" % CONTRADICTION_STALE)

    found = _hunt([V_AI / "BU.MD", V_RESEARCH / "CLAUDE.md", ROLD / "rails.toml"])
    for name, hits in found.items():
        note("%-14s %s" % (name, hits if hits else "(no dates of this class)"))
    if not any(CONTRADICTION_EXPECT in h for h in found.values()):
        red("the MEASURED date %s appears in NO control document - it should be somewhere"
            % CONTRADICTION_EXPECT)

    assertions, annotations = hunt_live_assertions()
    note("live tree: %d assertion(s), %d annotation(s) about the stale figure"
         % (len(assertions), len(annotations)))
    # 🔴 PRINT THE PATH, NOT THE BASENAME. Reporting "00_TOOLS_INDEX.md:52" made it
    # impossible to tell WHICH copy was flagged - the live one at Ai\00_TOOLS_INDEX.md, or
    # some duplicate elsewhere in the tree. Twenty minutes went into "fixing" a file that
    # was already correct because the finding named a file instead of naming a path.
    # C-16, VERIFY THE REFERENT, committed by the tool that exists to verify referents.
    for p, i in annotations:
        note("annotation (correct, left alone): %s:%d" % (p, i))
    for p, i, line in assertions:
        red("ASSERTS the stale %s -- %s:%d  |  %s" % (CONTRADICTION_STALE, p, i, line))
    if not assertions:
        ok("no LIVE document asserts %s" % CONTRADICTION_STALE)


def check_scar_count() -> None:
    head(7, "DID THE SCAR COUNT SURVIVE THE REBUILD")
    md = (ROLD / "SCARS.md").read_text(encoding="utf-8", errors="replace")
    n = len(re.findall(r"^## S-\d+", md, re.M))
    j = sum(1 for line in open(ROLD / "scars.jsonl", encoding="utf-8") if line.strip())
    if n == j:
        ok("SCARS.md headings=%d == scars.jsonl records=%d" % (n, j))
    else:
        red("DRIFT: SCARS.md headings=%d but scars.jsonl records=%d" % (n, j))


def check_r2_errors(log: pathlib.Path = None) -> None:
    head(8, "R2 PUBLISH - WHICH file failed, not how many times the counter printed")
    note("PLM-08's lesson: 'Errors: 1 (retrying may help)' is ONE CUMULATIVE COUNTER")
    note("reprinted as a progress heartbeat. Summing it is how 42.5 s became 970.3 s.")
    # 🔴 DISCOVER THE LOG, DO NOT HARDCODE A DATE INTO IT.
    # This defaulted to `TIDYUP_CLOSE_2026-08-11.log`, so on 2026-08-12 it was reading
    # YESTERDAY'S log and reporting yesterday's transfer failures as today's findings -
    # two of them, both already fixed. A dated filename baked into a checker is the
    # dated-handoff rot in a new costume: the check keeps answering a question about a
    # day that has passed, confidently.
    if log is None:
        candidates = [pathlib.Path(r"V:\Ai\_queue\R2_PUBLISH_LAST.log"),
                      MESH / "R2_PUBLISH_LAST.log",
                      WORKING / "R2_PUBLISH_LAST.log"]
        candidates += sorted(WORKING.glob("TIDYUP_CLOSE_*.log"), reverse=True)
        live = [p for p in candidates if p.exists()]
        if not live:
            note("no publish log found in any known location - NOT MEASURED")
            return
        log = max(live, key=lambda p: p.stat().st_mtime)
        note("newest publish log: %s (%s)" % (log, _age(log)))
    if not log.exists():
        red("publish log not found: %s" % log)
        return
    text = log.read_text(encoding="utf-8", errors="replace")
    heartbeats = len(re.findall(r"^Errors:\s+\d+", text, re.M))
    # Match rclone's actual ERROR line shape, not the bare word. A file in this archive is
    # literally named `PRIOR_DATA_ERRORS_2026-07-05.md`, so `"ERROR" in line` reported a
    # routine "checking" line as a publish failure. Reading a log without knowing its
    # grammar is the same defect as summing a cumulative counter (PLM-08) - and here it
    # would have manufactured an error on a clean publish.
    real = [line.strip() for line in text.splitlines()
            if re.search(r"\bERROR\s*:", line) and not line.startswith("Errors:")]
    distinct = sorted(set(real))
    # Anchor on the rclone line shape. A loose [^:]+? also swallowed "Attempt 1/3 failed
    # with 1 errors and", and reporting a retry banner as a FILENAME is the same class of
    # defect as summing a cumulative counter: reading a log without knowing its grammar.
    files = sorted(set(re.findall(r"ERROR : (\S+?): corrupted on transfer", text)))
    note("heartbeat lines: %d   distinct ERROR lines: %d" % (heartbeats, len(distinct)))
    if files:
        for f in files:
            red("failed transfer: %s" % f)
        note("all of these are files being APPENDED TO while rclone hashed them - the")
        note("publish log and R2_PUBLISH_LAST.log are written BY the publish itself.")
        note("md5 src != dst on a live file is a race, not disk corruption.")
    elif distinct:
        for line in distinct[:10]:
            red(line[:160])
    else:
        ok("no real error lines in the publish log")


def check_queue() -> None:
    head(9, "QUEUE - nothing stranded, nothing failed")
    r = subprocess.run(["py", "-3.14", str(MESH / "bts_runner.py"), "--status"],
                       capture_output=True, text=True, errors="replace")
    for line in (r.stdout or "").splitlines():
        print("        " + line.rstrip())
    if re.search(r"^\s*failed\s+[1-9]", r.stdout or "", re.M):
        red("there are FAILED jobs in the queue")
    if "STALE" in (r.stdout or ""):
        red("there are STALE jobs in running\\")


# --------------------------------------------------------------------------------------
def selftest() -> int:
    """NEGATIVE CONTROLS. Every check that makes a claim must be shown to FIRE.

    The three checks below are the three that were broken on 2026-08-11, and each is
    planted with the exact fault it failed to notice."""
    print("=" * 78)
    print("  tidyup2_checks --selftest")
    print("=" * 78)
    passed = []

    # 1. the contradiction hunt must find a planted stale date
    with tempfile.TemporaryDirectory() as d:
        p = pathlib.Path(d) / "x.md"
        p.write_text("expires %s\n" % CONTRADICTION_STALE, encoding="utf-8")
        got = _hunt([p]).get("x.md")
        passed.append(("contradiction hunt finds a planted stale date",
                       got == [CONTRADICTION_STALE]))

    # 2. the schema check must catch an entry missing `rule` - C-29's real fault
    with tempfile.TemporaryDirectory() as d:
        p = pathlib.Path(d) / "c.toml"
        p.write_text(
            '[[correction]]\nid="C-99"\nshort="s"\ndetail="body in the wrong key"\n'
            'count=1\nfirst=2026-01-01\nlast=2026-01-01\nstatus="OPEN"\n'
            'mechanism="none"\noccurrences=["one"]\n', encoding="utf-8")
        before = len(_reds)
        check_cos_schema(p)
        passed.append(("schema check catches an entry missing 'rule'",
                       len(_reds) > before))
        del _reds[before:]

    # 3. the schema check must catch a count with no evidence behind it
    with tempfile.TemporaryDirectory() as d:
        p = pathlib.Path(d) / "c.toml"
        p.write_text(
            '[[correction]]\nid="C-98"\nshort="s"\nrule="r"\ncount=5\n'
            'first=2026-01-01\nlast=2026-01-01\nstatus="OPEN"\nmechanism="none"\n'
            'occurrences=["only one"]\n', encoding="utf-8")
        before = len(_reds)
        check_cos_schema(p)
        passed.append(("schema check catches count=5 with 1 evidenced occurrence",
                       len(_reds) > before))
        del _reds[before:]

    # 4. the high-char scan must catch a planted emoji in a .bat
    with tempfile.TemporaryDirectory() as d:
        (pathlib.Path(d) / "planted.bat").write_text(
            "@echo off\r\nrem \U0001f534 red circle\r\n", encoding="utf-8")
        before = len(_reds)
        check_bat_charset([pathlib.Path(d)])
        passed.append(("high-char scan catches a planted emoji in a .bat",
                       len(_reds) > before))
        del _reds[before:]

    print()
    print("-" * 78)
    for label, good in passed:
        print("  %s  %s" % ("OK  " if good else "FAIL", label))
    bad = [l for l, g in passed if not g]
    print("SELFTEST PASS - every check was shown to fire on a planted fault."
          if not bad else "SELFTEST FAIL - %d check(s) cannot be trusted." % len(bad))
    return 1 if bad else 0


def main() -> int:
    if "--selftest" in sys.argv:
        return selftest()
    print("=" * 78)
    print("  TIDYUP2 - the adversarial pass")
    print("=" * 78)
    check_pointers()
    check_tool_drift()
    check_bat_charset()
    check_truncation()
    check_cos_schema()
    check_contradictions()
    check_scar_count()
    check_r2_errors()
    check_queue()
    print()
    print("=" * 78)
    print("  RESULT: %s   (%d red, %d notes)"
          % ("RED" if _reds else "GREEN", len(_reds), len(_notes)))
    print("=" * 78)
    for m in _reds:
        print("  RED   " + m)
    return 1 if _reds else 0


if __name__ == "__main__":
    sys.exit(main())
