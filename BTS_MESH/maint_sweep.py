#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""maint_sweep.py - the whole-machine maintenance measurement. Cowork, 2026-08-11.

Keith, 2026-08-11: "We are doing a dedicated plumbing session, and it's starting with
maintenance. That means known issues, fixits, todos before adding the new Ai node."
Then: "And the batteries, the quotas, the kmesh and kdash and bFast. Tools, indexes, etc."

WHAT THIS IS, AND WHAT IT IS NOT
-------------------------------
It MEASURES. It does not fix, and it writes nothing except its own report. Every number
it prints is read off disk or off the live filesystem in this run.

The organising idea is AGE, not correctness. Nearly every defect this mesh has found was
a number that was RIGHT when it was written and was still being displayed months later:
the GDX quota from 2026-07-13 (before the AI Plus purchase), Cowork's spend meter from
one 07-12 sample, the 2026-10-10 credit date that four live documents still asserted
five days after a document recorded "zero live references remain."

  ==> A MEASUREMENT WITHOUT A DATE IS A CLAIM. rails.toml already carries `measured` on
      every entry; nothing was ever reading those dates back. This does.

REFUSALS, each one paid for already
-----------------------------------
  * A missing value is NOT MEASURED. Never 0, never "-", never an empty string that a
    later reader will average. (bts_drive_health rendered "37 C of max 0 C" for a month.)
  * A number measured on one thing is never displayed against another. (dash.json shows
    V:'s 107 MB/s write speed against rails it does not describe.)
  * A count is reported next to WHAT IT COUNTS, so nobody sums a cumulative counter
    again. (PLM-08: 88 rclone heartbeats summed to 970 s for a 42.5 s job.)

ASCII ONLY ON STDOUT. A scheduler redirects this, and cp1252 kills a process that prints
an emoji (S-134). That rule is about the CLASS, not about .bat files.

USAGE
    py -3.14 maint_sweep.py              # measure, print, write the report
    py -3.14 maint_sweep.py --selftest   # negative controls
"""
from __future__ import annotations

import datetime as dt
import json
import pathlib
import re
import shutil
import sys
import tomllib

V_RESEARCH = pathlib.Path(r"V:\Research4")
V_AI = pathlib.Path(r"V:\Ai")
MESH = V_RESEARCH / "Ai" / "BTS_MESH"
ROLD = V_RESEARCH / "Ai" / "ROLD"
BFAST = V_AI / "BFast"
REPORT = V_RESEARCH / "Ai" / "PhD2_DATA_ARCHIVE" / "00_WORKING" / "MAINT_SWEEP_2026-08-11.md"

TODAY = dt.date(2026, 8, 11)
STALE_DAYS = 14
NOT_MEASURED = "NOT MEASURED"

_lines: list = []
_findings: list = []


def out(s: str = "") -> None:
    print(s)
    _lines.append(s)


def head(title: str) -> None:
    out("")
    out("=" * 78)
    out("  " + title)
    out("=" * 78)


def finding(sev: str, msg: str) -> None:
    _findings.append((sev, msg))
    out("  %-6s %s" % (sev, msg))


def age_days(d) -> int | None:
    if isinstance(d, dt.datetime):
        d = d.date()
    if isinstance(d, dt.date):
        return (TODAY - d).days
    if isinstance(d, str):
        m = re.match(r"(\d{4})-(\d{2})-(\d{2})", d)
        if m:
            return (TODAY - dt.date(*map(int, m.groups()))).days
    return None


def mtime_age(p: pathlib.Path) -> str:
    if not p.exists():
        return NOT_MEASURED
    ts = dt.datetime.fromtimestamp(p.stat().st_mtime)
    return "%s (%d d)" % (ts.strftime("%Y-%m-%d %H:%M"), (TODAY - ts.date()).days)


def load_json(p: pathlib.Path):
    """Truncation control done on BYTES, because that is the only thing it can be done on.

    🔴 FIRST VERSION WAS WRONG AND IT CRIED WOLF ON SIX HEALTHY FILES, INCLUDING
    TOOLS_REGISTRY.json - which it then declared "unreadable", killing section G entirely.
    It compared `len(read_text(...).encode())` against `stat().st_size`. On Windows,
    read_text does UNIVERSAL NEWLINE TRANSLATION: every CRLF becomes one LF, so a healthy
    CRLF file reads back SHORTER by exactly its line count. That is not truncation, it is
    the decoder doing its job.

    The irony is the point. This session has now watched four separate checks report a
    defect that was not there - verify_pointers on prose, the C.O.S. schema check on 29
    entries, my C-29 assertion on a 400-character window, and this. CLAUDE.md's rule
    holds in both directions: a check reporting a fault in a file you just touched is not
    evidence, and neither is a check reporting a fault in a file you did not.
    """
    try:
        data = p.read_bytes()
        if len(data) != p.stat().st_size:
            finding("RED", "short read on %s - %d bytes read, %d declared. THE MOUNT'S "
                           "TRUNCATION SIGNATURE."
                    % (p.name, len(data), p.stat().st_size))
            return None
        return json.loads(data.decode("utf-8"))
    except FileNotFoundError:
        return None
    except Exception as e:
        finding("RED", "%s does not parse: %s" % (p.name, e))
        return None


# ---------------------------------------------------------------- A. rails.toml ages
def sweep_rails_age() -> None:
    head("A. rails.toml - EVERY CONSTANT, BY AGE. A measurement without a date is a claim.")
    try:
        rails = tomllib.loads((ROLD / "rails.toml").read_text(encoding="utf-8"))
    except Exception as e:
        finding("RED", "rails.toml does not parse: %s" % e)
        return
    rows, owed, undated = [], [], []
    for section, items in rails.items():
        entries = items if isinstance(items, list) else [items]
        for e in entries:
            if not isinstance(e, dict):
                continue
            name = e.get("name") or e.get("id") or section
            if e.get("conf") == "U" and e.get("owed"):
                owed.append((section, name, str(e["owed"])[:96]))
            a = age_days(e.get("measured"))
            if a is None:
                if e.get("conf") == "V":
                    undated.append((section, name))
            else:
                # 🔴 A [[clock]] IS A DATE, NOT A READING, so it cannot go stale.
                # "The Vertex credit expires 2026-10-13" was measured on 2026-07-31 and is
                # exactly as true today; ageing it produces a permanent AMBER that can
                # never be cleared by anything except re-measuring a fact that has not
                # changed. A check that cannot be satisfied gets muted. Staleness applies
                # to things that DRIFT - quotas, speeds, spend - not to fixed future dates.
                if section == "clock":
                    continue
                rows.append((a, section, name, e.get("conf", "?")))
    rows.sort(reverse=True)
    out("  %-5s %-14s %-34s %s" % ("AGE", "SECTION", "NAME", "CONF"))
    out("  " + "-" * 74)
    for a, section, name, conf in rows:
        flag = "  <== STALE" if a > STALE_DAYS else ""
        out("  %-5s %-14s %-34s %s%s" % ("%dd" % a, section, str(name)[:34], conf, flag))
    stale = [r for r in rows if r[0] > STALE_DAYS]
    out("")
    out("  %d dated entries | %d older than %d days | %d conf=V with NO measured date"
        % (len(rows), len(stale), STALE_DAYS, len(undated)))
    for section, name in undated:
        finding("RED", "conf=V but no measured date: [%s] %s -- 'V' means verified ON A "
                       "DATE; without one it is an assertion" % (section, name))
    if stale:
        # Name the ACTUAL oldest entries. The previous wording hardcoded "the GDX quota is
        # the known-worst" - true when written, false the moment GDX was re-measured, and
        # it then kept pointing at a fixed entry while the real oldest went unnamed. A
        # finding that names a specific culprit must derive it, or it becomes the same
        # copied-fact rot it is reporting.
        worst = ", ".join("%s (%dd)" % (r[2], r[0]) for r in stale[:3])
        finding("AMBER", "%d rails.toml entries are older than %d days. Oldest: %s"
                % (len(stale), STALE_DAYS, worst))
    out("")
    out("  STILL OWED (conf=U with an `owed` note):")
    for section, name, why in owed:
        out("    [%s] %-26s %s" % (section, str(name)[:26], why))


# ---------------------------------------------------------------- B. batteries
def sweep_batteries() -> None:
    head("B. THE BATTERIES - every meter, its last entry, and whether anything reads it")
    ledgers = [
        ("SGH / xAI", MESH / "sgh_spend.json"),
        ("GW / grok-build", MESH / "gw_spend.json"),
        ("CoPG credits", MESH / "cop_spend.json"),
        ("OA / OpenAI", MESH / "oa_spend.json"),
        ("Vertex", MESH / "vertex_usage.json"),
        ("GEM quota", MESH / "gem_quota.json"),
        ("Cowork budget", MESH / "claude_budget.json"),
        ("KDash meters", MESH / "meters.json"),
        ("drive health", MESH / "drive_health.json"),
    ]
    out("  %-18s %-26s %-12s %s" % ("BATTERY", "LAST WRITTEN", "BYTES", "CONTENT"))
    out("  " + "-" * 74)
    for label, p in ledgers:
        if not p.exists():
            out("  %-18s %-26s %-12s %s" % (label, NOT_MEASURED, "-", "FILE ABSENT"))
            finding("AMBER", "%s ledger absent: %s" % (label, p.name))
            continue
        d = load_json(p)
        summary = ""
        if isinstance(d, dict):
            for key in ("WORK", "total_usd", "mtd_usd", "spent", "credits",
                        "calls", "unpriced", "unpriced_calls"):
                if key in d:
                    summary += "%s=%s  " % (key, d[key])
            if not summary:
                summary = "keys: " + ",".join(list(d)[:5])
        elif isinstance(d, list):
            summary = "%d record(s)" % len(d)
        out("  %-18s %-26s %-12s %s"
            % (label, mtime_age(p), format(p.stat().st_size, ","), summary[:34]))

    out("")
    out("  THE TWO DENOMINATORS THAT ARE STILL UNKNOWN, and both are measurable:")
    out("    CoPG  - GitHub publishes NO Free-plan credit allowance, in the docs OR in the")
    out("            account. Derive it: cap = credits_spent / (pct_used/100). One tick")
    out("            from 0%% to 1%% pins it. Until then only a LOWER BOUND is honest.")
    out("    OA    - `codex` -> /status has never been read. Every number about OA's limits")
    out("            currently comes off a PRICING PAGE, not off the account.")
    shape = load_json(MESH / "oa_usage_shape.json")
    if shape:
        out("    OA usage shape learned: %s" % str(shape)[:120])
    else:
        finding("AMBER", "oa_usage_shape.json is empty or absent - OA token usage is NOT "
                         "reaching the ledger. An unmetered prepaid rail fails as a "
                         "refusal in the middle of something else, not as a bill.")


# ---------------------------------------------------------------- C. quotas
def sweep_quotas() -> None:
    head("C. QUOTAS AND SURFACES - measured live, next to what rails.toml still claims")
    out("  %-8s %-30s %10s %10s %8s" % ("DRIVE", "LABEL", "TOTAL GB", "FREE GB", "USED %"))
    out("  " + "-" * 74)
    for letter, label in (("V:", "research tree"), ("C:", "boot"), ("D:", "Passport"),
                          ("X:", "GDX / Google Drive"), ("L:", "Cruzer")):
        try:
            u = shutil.disk_usage(letter + "\\")
            out("  %-8s %-30s %10.1f %10.1f %7.1f%%"
                % (letter, label, u.total / 2**30, u.free / 2**30,
                   100.0 * u.used / u.total if u.total else 0))
        except OSError as e:
            out("  %-8s %-30s %10s %10s %8s"
                % (letter, label, NOT_MEASURED, NOT_MEASURED, "-"))
            out("           (%s)" % str(e)[:60])

    try:
        rails = tomllib.loads((ROLD / "rails.toml").read_text(encoding="utf-8"))
    except Exception:
        return
    out("")
    out("  WHAT rails.toml RECORDS FOR EACH SURFACE:")
    for s in rails.get("surface", []):
        a = age_days(s.get("measured"))
        out("    %-14s %-40s %s"
            % (str(s.get("name"))[:14],
               str(s.get("quota") or s.get("note") or s.get("utility") or "")[:40],
               ("%d d old" % a) if a is not None else "NO DATE"))
        if a is not None and a > STALE_DAYS:
            finding("AMBER", "surface '%s' last measured %d days ago" % (s.get("name"), a))


# ---------------------------------------------------------------- D. KDash
def sweep_kdash() -> None:
    head("D. KDASH - dash.json, and the figure that is displayed against the wrong thing")
    p = MESH / "dash.json"
    out("  dash.json last written : %s" % mtime_age(p))
    d = load_json(p)
    if not d:
        finding("RED", "dash.json absent or unparseable - KDash renders THIS file")
        return
    blob = json.dumps(d)
    out("  size                   : %s bytes" % format(p.stat().st_size, ","))

    # The 107 MB/s propagation. V:'s write speed, rendered against lanes it does not describe.
    # Count only BARE occurrences. A labeled one - "107 MB/s on V: Ai (surface write
    # speed, NOT rail throughput)" - is the FIX, not the defect, and counting it as a hit
    # is the same mistake as flagging "any 2026-10-10 you see is stale" as an assertion
    # of 2026-10-10. Third time tonight a check has cried wolf over its own repair.
    labeled = blob.count("surface write speed, NOT rail throughput")
    total = blob.count("107 MB/s")
    bare = blob.count('"107 MB/s"')
    out("  '107 MB/s' total / labeled / BARE : %d / %d / %d" % (total, labeled, bare))
    if bare:
        finding("RED", "'107 MB/s' appears BARE %d times in dash.json. That is V:'s WRITE "
                       "SPEED rendered against rails it does not describe - one thing "
                       "measured, another thing displayed." % bare)
    elif labeled:
        out("  (every one names the surface it belongs to, so it cannot be read as the")
        out("   rail's own throughput. The number was always right; the column lied.)")

    n_unmeasured = blob.count("UNMEASURED") + blob.count("NOT MEASURED")
    out("  UNMEASURED markers      : %d" % n_unmeasured)
    for lane in ("cli-grok", "cli-gemini", "cli-claude", "bfast-handoff"):
        present = lane in blob
        out("    %-16s in dash.json: %s" % (lane, present))
        if not present:
            finding("AMBER", "lane '%s' is not in dash.json at all" % lane)
    if n_unmeasured:
        out("  (UNMEASURED rendering as a WORD rather than a number is CORRECT - that is")
        out("   bts_kdash_feed's rule and it is holding.)")


# ---------------------------------------------------------------- E. BFast
def sweep_bfast() -> None:
    head("E. BFAST - the config authority, and whether its roots actually resolve")
    cfg = BFAST / "roots.json"
    out("  roots.json             : %s" % mtime_age(cfg))
    d = load_json(cfg)
    if not d:
        finding("RED", "BFast roots.json absent or unparseable - it is the config authority")
        return
    for r in d.get("roots", []):
        p = pathlib.Path(r["path"])
        exists = p.exists()
        writable = False
        if exists:
            try:
                probe = p / ".bfast_write_probe.tmp"
                probe.write_text("probe", encoding="ascii")
                probe.unlink()
                writable = True
            except OSError:
                writable = False
        out("    %-12s %-38s exists=%-6s write=%s"
            % (r["name"], r["path"], exists, writable if exists else "-"))
        if not exists:
            finding("RED", "BFast root '%s' -> %s DOES NOT EXIST. roots.json says a "
                           "missing root must hard-error, never read as empty."
                    % (r["name"], r["path"]))
        elif r.get("write") and not writable:
            finding("AMBER", "BFast root '%s' is declared write=true but is not writable"
                    % r["name"])

    dup = V_RESEARCH / "Ai" / "BTS_MCP" / "roots.json"
    out("")
    out("  superseded duplicate config present: %s" % dup.exists())
    if dup.exists():
        finding("AMBER", "V:\\Research4\\Ai\\BTS_MCP\\roots.json still exists. BFast's own "
                         "roots.json calls it SUPERSEDED. Two homes for one config is a "
                         "copy, and copies rot - stage it to _delme once every client "
                         "launches bfast.py from V:\\Ai\\BFast.")
    # Only a DECLARED audit log can be missing. Until 2026-08-12 roots.json declared
    # `auditLog: logs/bfast_audit.jsonl` and nothing in bfast.py ever wrote it - a config
    # asserting a capability the code does not have. The claim was removed rather than the
    # check silenced, so this now reports the honest state: no audit is promised, and none
    # exists.
    declared = (d.get("auditLog") or "").strip()
    if declared:
        audit = BFAST / declared
        out("  audit log (declared)   : %s -> %s" % (declared, mtime_age(audit)))
        if not audit.exists():
            finding("AMBER", "roots.json DECLARES auditLog '%s' and the file does not "
                             "exist. Either nothing has used BFast, or the audit is "
                             "declared and not implemented - and those are very "
                             "different." % declared)
    else:
        out("  audit log              : none declared (the false claim was removed "
            "2026-08-12; BFast records nothing about who read or wrote what)")


# ---------------------------------------------------------------- F. KMesh
def sweep_kmesh() -> None:
    head("F. KMESH - identity, and the federation claim that must stay FALSE")
    sys.path.insert(0, str(MESH))
    try:
        import bts_identity as bi
        out("  MESH_ID                : %s" % getattr(bi, "MESH_ID", "?"))
        out("  OWNER                  : %s" % getattr(bi, "OWNER", "?"))
        peers = getattr(bi, "PEERS", {})
        out("  PEERS                  : %s" % ", ".join(peers) if peers else "none")
        ready = bi.federation_ready()
        val = ready[0] if isinstance(ready, tuple) else ready
        blockers = ready[1] if isinstance(ready, tuple) and len(ready) > 1 else []
        out("  federation_ready()     : %s" % val)
        out("  blockers               : %d" % len(blockers))
        for i, b in enumerate(blockers, 1):
            out("    %d. %s" % (i, str(b).split(".")[0][:96]))
        if val is True:
            finding("RED", "federation_ready() returned TRUE. Do not report the "
                           "mesh-of-meshes as working without re-measuring every blocker.")
        # 🔴 COUNT THE BLOCKERS, DO NOT QUOTE A REMEMBERED NUMBER. Measured 2026-08-11:
        # the code returns FIVE. CLAUDE.md, BU.MD and 00_TOOLS_INDEX.md all say FOUR.
        # GW added the fifth (no notarization of control files - a green verify_pointers
        # run is a point-in-time claim, and any node may rewrite a control file
        # afterwards, so the next green run certifies it silently: TOCTOU) on 2026-07-31,
        # and the prose was never updated. A hardcoded count in a docstring is a COPY of
        # a fact, and copies rot - the dated-handoff lesson, in a sentence.
        # CHECK THE DOCUMENTS, DO NOT ASSUME THEM. The first version fired whenever the
        # count was not 4 - so it kept firing after the prose had been corrected, which
        # is a check that can never close and therefore gets muted.
        n = len(blockers)
        words = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six"}
        wrong = []
        for doc in (V_RESEARCH / "CLAUDE.md", V_AI / "BU.MD",
                    V_RESEARCH / "Ai" / "00_TOOLS_INDEX.md",
                    MESH / "TOOLS_REGISTRY.json"):
            if not doc.exists():
                continue
            # LINE BY LINE, AND SKIP ANNOTATIONS. Both documents now correctly say FIVE
            # *and* carry a sentence recording that they said "4 blockers" until today.
            # A whole-file substring search cannot tell a live claim from the note about
            # the claim it replaced - which is the same distinction the stale-date hunt
            # had to learn, in a different file, four hours earlier.
            for line in doc.read_bytes().decode("utf-8", "replace").splitlines():
                low = line.lower()
                if any(m in low for m in ("said", "until", "was ", "corrected",
                                          "superseded", "from 2026")):
                    continue
                hit = next((b for b in range(1, 7) if b != n
                            and (("%d blockers" % b) in low
                                 or ("%s blockers" % words[b]) in low)), None)
                if hit:
                    wrong.append("%s says %s" % (doc.name, words[hit]))
                    break
        if wrong:
            finding("AMBER", "federation_ready() returns %d blockers but %s. The %dth is "
                             "GW's notarization/TOCTOU blocker, added 2026-07-31. "
                             "DO NOT COUNT IN PROSE - ASK THE FUNCTION."
                    % (n, "; ".join(wrong), n))
    except Exception as e:
        finding("RED", "bts_identity did not import: %s" % e)


# ---------------------------------------------------------------- G. indexes
def sweep_indexes() -> None:
    head("G. TOOLS AND INDEXES - both hand-maintained, no generator, drifts BOTH ways")
    reg = load_json(MESH / "TOOLS_REGISTRY.json")
    idx_p = V_RESEARCH / "Ai" / "00_TOOLS_INDEX.md"
    if not reg:
        finding("RED", "TOOLS_REGISTRY.json unreadable")
        return
    tools = reg["tools"]
    idx = idx_p.read_text(encoding="utf-8", errors="replace").lower()
    reg_blob = json.dumps(tools).lower()
    out("  registry entries       : %d   (_updated %s)" % (len(tools), reg.get("_updated")))
    out("  index page             : %s bytes, %s"
        % (format(idx_p.stat().st_size, ","), mtime_age(idx_p)))

    missing = []
    for root in (MESH, ROLD, V_AI / "_session_logs"):
        if not root.is_dir():
            continue
        for p in sorted(root.glob("*.py")):
            if p.name.startswith("_"):
                continue
            if p.stem.lower() not in reg_blob and p.stem.lower() not in idx:
                missing.append(p.name)
    out("  .py in NEITHER index   : %d" % len(missing))
    if missing:
        finding("AMBER", "%d .py files are in neither index. Two rebuilds have already "
                         "happened because a tool nobody pointed at could not be found; "
                         "one reimplemented 7 of 8 existing verbs." % len(missing))
        for i in range(0, len(missing), 6):
            out("      " + ", ".join(missing[i:i + 6]))

    bad = [t.get("id") for t in tools
           if (t.get("conf") == "V" and not t.get("measured"))
           or (t.get("conf") == "U" and not t.get("owed"))]
    if bad:
        finding("RED", "registry conf-schema violations: %s" % bad)
    else:
        out("  conf schema            : clean (V carries measured, U carries owed)")

    weird = [p for p in MESH.iterdir() if p.is_dir() and len(p.name) > 40
             and "\\" not in p.name and re.match(r"^[A-Z]:?[A-Za-z0-9_]{30,}", p.name)]
    for p in weird:
        finding("AMBER", "directory named after a FLATTENED PATH: %s -- a path was used "
                         "as a filename, which is the same class as the 127 files all "
                         "named audit.jsonl" % p.name)


# ---------------------------------------------------------------- selftest
def selftest() -> int:
    """The claim under test is that this sweep REFUSES TO INVENT A NUMBER."""
    checks = []
    checks.append(("a missing date reports None, not 0", age_days(None) is None))
    checks.append(("a bad date string reports None", age_days("not a date") is None))
    checks.append(("a real date measures", age_days("2026-08-01") == 10))
    checks.append(("a datetime.date measures", age_days(dt.date(2026, 7, 28)) == 14))
    p = pathlib.Path(r"V:\definitely\not\here.json")
    checks.append(("an absent file reports NOT MEASURED", mtime_age(p) == NOT_MEASURED))
    checks.append(("an absent json returns None, not {}", load_json(p) is None))

    # The truncation control, in BOTH directions. The first version of load_json fired on
    # six healthy files because CRLF->LF translation made read_text shorter than stat.
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        crlf = pathlib.Path(d) / "crlf.json"
        crlf.write_bytes(b'{\r\n "a": 1,\r\n "b": 2\r\n}\r\n')
        before = len(_findings)
        got = load_json(crlf)
        checks.append(("a healthy CRLF json is NOT called truncated",
                       got == {"a": 1, "b": 2} and len(_findings) == before))
        del _findings[before:]

        good = pathlib.Path(d) / "lf.json"
        good.write_bytes(b'{"a": 1}')
        before = len(_findings)
        checks.append(("a healthy LF json parses", load_json(good) == {"a": 1}
                       and len(_findings) == before))
        del _findings[before:]

        bad = pathlib.Path(d) / "broken.json"
        bad.write_bytes(b'{"a": 1, "b": ')
        before = len(_findings)
        checks.append(("a genuinely malformed json is caught, not returned",
                       load_json(bad) is None and len(_findings) > before))
        del _findings[before:]
    print("=" * 78)
    print("  maint_sweep --selftest")
    print("=" * 78)
    for label, good in checks:
        print("  %s  %s" % ("OK  " if good else "FAIL", label))
    bad = [l for l, g in checks if not g]
    print("SELFTEST PASS - a missing value is NOT MEASURED, never a zero."
          if not bad else "SELFTEST FAIL - %d check(s)." % len(bad))
    return 1 if bad else 0


def main() -> int:
    if "--selftest" in sys.argv:
        return selftest()
    out("# MAINTENANCE SWEEP - 2026-08-11 (PLUMBING)")
    out("")
    out("Measured, not read off a status file. Mesh document: .md is correct, Cowork and")
    out("the nodes are the consumer. Never convert, never present.")
    sweep_rails_age()
    sweep_batteries()
    sweep_quotas()
    sweep_kdash()
    sweep_bfast()
    sweep_kmesh()
    sweep_indexes()

    head("FINDINGS")
    reds = [m for s, m in _findings if s == "RED"]
    ambers = [m for s, m in _findings if s == "AMBER"]
    out("  %d RED, %d AMBER" % (len(reds), len(ambers)))
    for m in reds:
        out("  RED    " + m)
    for m in ambers:
        out("  AMBER  " + m)
    out("")
    out("  NOTHING HERE WAS FIXED. This pass measures; the fixes are separate and each")
    out("  one has to be asserted against its own artifact afterwards (C-29).")

    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text("\n".join(_lines) + "\n", encoding="utf-8")
    print()
    print("  report written: %s (%s bytes)"
          % (REPORT, format(REPORT.stat().st_size, ",")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
