#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""bts_health.py - THE JOB THAT MAKES PLUMBING SESSIONS UNNECESSARY. 2026-08-12.

Keith, 2026-08-12: "This system needs to be one that doesn't require plumbing sessions at
all. It should be robust and just run."

He is right, and the evidence is this session. Every defect it found was findable by a
script, and every one had been sitting for days or weeks:

    the checker crying wolf over prose ............ 12 days
    the KDash fixture asserting the opposite ...... 11 days
    "four blockers" when the function said five ... 11 days
    three monitors shown RED while working ........ 13 days
    the stale credit date "verified fixed" ........  5 days (22 live references)
    the GDX quota recorded before the purchase .... 29 days
    Cowork's own spend meter ...................... 31 days

NOT ONE of those needed a human to find. They needed something to LOOK, on a schedule,
and to be capable of saying so. The checks existed. What did not exist was anything that
ran them without being asked.

  ==> A PLUMBING SESSION IS WHAT YOU DO WHEN NOTHING WATCHES. The fix is not a better
      session; it is to stop needing one.

THE THREE PROPERTIES THAT MAKE "IT JUST RUNS" TRUE
--------------------------------------------------
1. **IT RUNS WITHOUT BEING ASKED.** Daily, native, no screen.

2. **SILENCE IS IMPOSSIBLE.** This is the deepest lesson of the session and the one that
   is easiest to get wrong. `BTS Queue Runner` stalled for 43 minutes and its own ledger
   COULD NOT SAY SO, because a ledger written only on activity makes "idle" and "dead"
   identical. So this writes a HEARTBEAT every run, pass or fail. An absent heartbeat is
   itself the alarm. **A monitor that only speaks when it is unhappy cannot be
   distinguished from a monitor that has died.**

3. **IT ONLY INTERRUPTS ON RED.** Everything green goes to a file nobody has to read.
   A report that always speaks trains everyone to stop listening - which is exactly how
   three RED monitors sat ignored on KDash for thirteen days.

WHAT IT DOES NOT DO, DELIBERATELY
---------------------------------
It does not FIX. It measures, records, and escalates. Every automatic repair this session
attempted needed a judgement call that a cron job has no business making - which key was
authoritative, whether a copy or the original was the truth, whether a number was stale or
simply unchanged. **Automation that repairs without judgement is how a healthy file gets
"corrected" into damage**, and four checks tonight would have done exactly that.

USAGE
    py -3.14 bts_health.py            # the daily pass
    py -3.14 bts_health.py --selftest # negative controls
"""
from __future__ import annotations

import datetime as dt
import json
import pathlib
import subprocess
import sys

MESH = pathlib.Path(__file__).resolve().parent
ROLD = MESH.parent / "ROLD"
AI = pathlib.Path(r"V:\Ai")
WORKING = MESH.parent / "PhD2_DATA_ARCHIVE" / "00_WORKING"
HEARTBEAT = AI / "_queue" / "health_heartbeat.json"
REPORT = WORKING / "HEALTH_%s.md"
ALERT = AI / "_queue" / "HEALTH_ALERT.md"

# Every check that has ever caught something real. Each returns (ok, headline, detail).
CHECKS = [
    ("pointers", ROLD / "verify_pointers.py", []),
    ("conf schema", ROLD / "verify_conf.py", []),
    ("corrections", ROLD / "corrections.py", ["--selftest"]),
    ("scars", ROLD / "scars.py", ["--selftest"]),
    ("tools index vs registry", MESH / "tools_sync.py", ["--check"]),
    ("mesh sweep", MESH / "maint_sweep.py", []),
    ("adversarial (mechanical)", MESH / "tidyup2_checks.py", []),
    ("adversarial (counts)", MESH / "tidyup2_full.py", []),
    ("queue runner liveness", MESH / "runner_doctor.py", ["--check"]),
    ("disks", MESH / "disk_guard.py", []),
]

PY = ["py", "-3.14"]


def run_one(name, path, args, timeout=600):
    if not path.exists():
        return (False, "%s: TOOL MISSING at %s" % (name, path), "")
    try:
        r = subprocess.run(PY + [str(path)] + args, capture_output=True, text=True,
                           errors="replace", timeout=timeout)
    except subprocess.TimeoutExpired:
        return (False, "%s: TIMED OUT after %ds" % (name, timeout), "")
    except Exception as e:                                          # noqa: BLE001
        return (False, "%s: did not run: %s" % (name, e), "")
    out = r.stdout or ""
    # rc 2 means FINDINGS (PLM-44), not breakage - but findings still escalate.
    ok = r.returncode == 0
    lines = [l.strip() for l in out.splitlines()
             if l.strip().startswith(("RED", "T2-", "DRIFT", "FAIL"))]
    head = "%s: %s" % (name, "ok" if ok else "%d finding(s)" % max(len(lines), 1))
    return (ok, head, "\n".join(lines[:12]))


def beat(status, reds):
    """Write the heartbeat ALWAYS. Its absence is the alarm."""
    HEARTBEAT.parent.mkdir(parents=True, exist_ok=True)
    prev = {}
    if HEARTBEAT.exists():
        try:
            prev = json.loads(HEARTBEAT.read_bytes().decode("utf-8"))
        except ValueError:
            prev = {}
    rec = {"last_run": dt.datetime.now().isoformat(timespec="seconds"),
           "status": status, "red_count": len(reds), "reds": reds[:20],
           "run_count": int(prev.get("run_count", 0)) + 1,
           "_readme": ("Written on EVERY run, pass or fail. If `last_run` is older than "
                       "~26 h, THIS JOB is what has failed - not the mesh. A monitor that "
                       "speaks only when unhappy cannot be told apart from a dead one.")}
    with open(HEARTBEAT, "w", encoding="utf-8", newline="") as fh:
        fh.write(json.dumps(rec, indent=1))
    return rec


def heartbeat_age_hours():
    if not HEARTBEAT.exists():
        return None
    try:
        d = json.loads(HEARTBEAT.read_bytes().decode("utf-8"))
        t = dt.datetime.fromisoformat(d["last_run"])
        return (dt.datetime.now() - t).total_seconds() / 3600.0
    except Exception:                                               # noqa: BLE001
        return None


def main() -> int:
    started = dt.datetime.now()
    lines = ["# MESH HEALTH — %s" % started.strftime("%Y-%m-%d %H:%M"),
             "",
             "Written by `bts_health.py`, unattended. Mesh document; `.md` is correct.",
             ""]
    reds, results = [], []
    for name, path, args in CHECKS:
        ok, head, detail = run_one(name, path, args)
        results.append((ok, head, detail))
        lines.append("- %s **%s**" % ("✅" if ok else "🔴", head))
        if detail:
            lines += ["", "```", detail, "```", ""]
        if not ok:
            reds.append(head)

    prev_age = heartbeat_age_hours()
    if prev_age is not None and prev_age > 26:
        reds.append("THIS JOB did not run for %.1f h — the watcher itself stopped"
                    % prev_age)

    status = "GREEN" if not reds else "RED"
    lines += ["", "---", "", "## RESULT: **%s** — %d check(s), %d red"
              % (status, len(CHECKS), len(reds))]
    if reds:
        lines.append("")
        for r in reds:
            lines.append("- 🔴 %s" % r)

    WORKING.mkdir(parents=True, exist_ok=True)
    out = pathlib.Path(str(REPORT) % started.strftime("%Y-%m-%d"))
    with open(out, "w", encoding="utf-8", newline="") as fh:
        fh.write("\n".join(lines) + "\n")

    rec = beat(status, reds)

    # ONLY RED PRODUCES AN ALERT FILE. Green leaves nothing to read, on purpose:
    # a report that always speaks trains everyone to stop listening.
    if reds:
        with open(ALERT, "w", encoding="utf-8", newline="") as fh:
            fh.write("# MESH HEALTH: RED — %s\n\n%s\n\nFull report: %s\n"
                     % (started.strftime("%Y-%m-%d %H:%M"),
                        "\n".join("- %s" % r for r in reds), out))
    elif ALERT.exists():
        ALERT.unlink()

    print("=" * 78)
    print("  MESH HEALTH  %s   run #%d" % (status, rec["run_count"]))
    print("=" * 78)
    for ok, head, _ in results:
        print("  %s  %s" % ("ok  " if ok else "RED ", head))
    print("-" * 78)
    print("  report    : %s" % out)
    print("  heartbeat : %s" % HEARTBEAT)
    print("  alert     : %s" % (ALERT if reds else "none (green)"))
    return 0 if not reds else 2


def selftest() -> int:
    import tempfile
    global HEARTBEAT, ALERT
    real_hb, real_al = HEARTBEAT, ALERT
    checks = []
    try:
        d = pathlib.Path(tempfile.mkdtemp(prefix="health_"))
        HEARTBEAT, ALERT = d / "hb.json", d / "alert.md"

        beat("GREEN", [])
        checks.append(("a GREEN run still writes a heartbeat", HEARTBEAT.exists()))
        r1 = json.loads(HEARTBEAT.read_text(encoding="utf-8"))
        beat("RED", ["something"])
        r2 = json.loads(HEARTBEAT.read_text(encoding="utf-8"))
        checks.append(("the run counter increments",
                       r2["run_count"] == r1["run_count"] + 1))
        checks.append(("the heartbeat records the red count", r2["red_count"] == 1))
        age = heartbeat_age_hours()
        checks.append(("heartbeat age reads back as ~0 h",
                       age is not None and age < 1))

        HEARTBEAT.unlink()
        checks.append(("an ABSENT heartbeat reports None, not 0",
                       heartbeat_age_hours() is None))

        missing_ok, missing_head, _ = run_one("ghost", d / "nope.py", [])
        checks.append(("a MISSING tool is a RED, not a silent skip",
                       not missing_ok and "MISSING" in missing_head))
    finally:
        HEARTBEAT, ALERT = real_hb, real_al

    print("=" * 78)
    print("  bts_health --selftest")
    print("=" * 78)
    for label, good in checks:
        print("  %s  %s" % ("OK  " if good else "FAIL", label))
    bad = [l for l, g in checks if not g]
    print("SELFTEST PASS - it beats on green, counts runs, and refuses to skip a missing "
          "tool." if not bad else "SELFTEST FAIL - %d check(s)." % len(bad))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(selftest() if "--selftest" in sys.argv else main())
