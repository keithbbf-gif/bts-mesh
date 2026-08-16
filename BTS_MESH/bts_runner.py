#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""bts_runner.py - the background execution lane. Cowork, 2026-08-11.

WHAT THIS CLOSES
----------------
`PLM-25`, owed since 2026-07-30: *"a sanctioned long-job route - a native
scheduled task, or a CoW-side runner - written down, so the next session does not
rediscover this by losing a return."*

The constraints that make it necessary, all measured:
  * The Linux sandbox caps a bash call at 45 s, and `nohup`/`setsid nohup` both die
    when the call returns, silently, leaving an empty output file.
  * The sandbox cannot run a Windows `.bat` at all, cannot reach `V:` as a drive
    letter, and `bts_sgh._save()` dies across the FUSE mount - so no paid call made
    from there can record its own spend.
  * Cowork driving File Explorer works, but it uses Keith's screen for every run.

    ==> So: a NATIVE Windows scheduled task, every minute, watching a queue folder.
    Cowork writes a file into the queue; it runs; the log lands where Cowork reads.
    No screen, no click, no 45-second ceiling.

DESIGN RULES, each one paid for already
---------------------------------------
  * **A job runs EXACTLY ONCE.** It is claimed by RENAMING it into `running\\`
    before execution - an atomic rename on one volume - so two overlapping ticks
    cannot both take it. Nothing relies on a lock file nobody checks.
  * **A timeout must SAY SO.** `bts_deadline.py`'s rule: write RUNNING first, then
    the outcome, or leave RED - TIMED OUT. No outcome ever leaves a silent empty
    file.
  * **Every job's log opens FIRST and captures both streams**, because `pause` is
    not a report and a job that fails invisibly is worse than one that never ran.
  * **Nothing is deleted, ever.** Finished jobs MOVE to `done\\` or `failed\\`.
  * **A missing queue directory is created, not assumed.**

USAGE
    python bts_runner.py --once        # one tick; what the scheduled task calls
    python bts_runner.py --status      # what is queued, running, done, failed
    python bts_runner.py --selftest    # negative control
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

QUEUE_ROOT = Path(r"V:\Ai\_queue")
PENDING = QUEUE_ROOT
RUNNING = QUEUE_ROOT / "running"
DONE = QUEUE_ROOT / "done"
FAILED = QUEUE_ROOT / "failed"
FINDINGS = QUEUE_ROOT / "done" / "findings"

# 🔴 PLM-44 — "THE JOB BROKE" AND "THE JOB FOUND SOMETHING" ARE DIFFERENT EVENTS.
# Measured 2026-08-12: `tidyup2_seal` was filed under failed\ because it exited 1 — and it
# exited 1 because it CORRECTLY found that the handoff claimed 103 registry tools while
# the registry held 104. It did exactly its job and was recorded as a failure, because a
# non-zero exit was all the runner could see.
# ⇒ A working control lands in failed\, where the next reader either ignores real failures
#   or investigates finished work. That is the same shape as everything else this mesh has
#   been fixing: a report that cannot separate two states gets read as whichever the
#   reader expects.
# ⇒ THREE OUTCOMES NOW:  0 = CLEAN · 2 = FINDINGS · anything else = BROKE.
#   A job that returns 2 moves to done\findings\ and the ledger records the WORD, not just
#   the number — because "rc: 2" in a ledger is exactly as ambiguous as "rc: 1" was.
RC_CLEAN = 0
RC_FINDINGS = 2
LOGS = QUEUE_ROOT / "logs"
LEDGER = QUEUE_ROOT / "runner_ledger.jsonl"

RUNNABLE = {".bat": None, ".cmd": None, ".py": "py -3.14", ".ps1": None}
DEFAULT_TIMEOUT = 1800          # 30 min. A job that needs longer says so in its name.
STALE_RUNNING_SECS = 7200       # a job stuck in running\ for 2 h is reported, not retried

# 🔴 THE QUEUE ROOT IS A JOB INBOX, NOT A SCRATCH DIRECTORY - added 2026-08-11, same day,
# found by TidyUP2 in this file's OWN first day of service.
#
# `_tidyup2_checks.py` was placed in V:\Ai\_queue\ for a .bat to call. The runner did exactly
# what it was built to do: it saw a .py, CLAIMED it by renaming it into running\, and executed
# it. The bat then failed with "can't open file ... No such file or directory" - because the
# runner had moved the helper out from under the job that was calling it.
#
# Neither piece was wrong on its own. The CONVENTION ("_ means helper, not job") existed only
# inside _tidyup2_checks.py's own header, where tick() could not see it. A convention that
# lives in a comment in one file is not a convention, it is a hope.
#
# ==> The rule is now IN THE RUNNER, which is the only place that can enforce it.
# ==> And helpers belong in BTS_MESH\ anyway. This skip is a guard rail, not a licence.
HELPER_PREFIX = "_"


def _is_helper(path: Path) -> bool:
    """A `_`-prefixed file in the queue root is a SUPPORTING FILE, never a job.

    Reported by --status rather than silently ignored: an invisible skip is how a job that
    should have run looks identical to a job that did."""
    return path.name.startswith(HELPER_PREFIX)


def _dirs():
    for d in (QUEUE_ROOT, RUNNING, DONE, FAILED, LOGS, FINDINGS):
        d.mkdir(parents=True, exist_ok=True)


def _cmd_for(path: Path) -> list:
    ext = path.suffix.lower()
    if ext in (".bat", ".cmd"):
        return ["cmd", "/c", "call", str(path)]
    if ext == ".py":
        return ["py", "-3.14", str(path)]
    if ext == ".ps1":
        return ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(path)]
    return []


def _timeout_for(path: Path) -> int:
    """A job may request its own ceiling by embedding `__tNNNN` in its filename."""
    stem = path.stem
    if "__t" in stem:
        tail = stem.rsplit("__t", 1)[-1]
        digits = "".join(c for c in tail if c.isdigit())
        if digits:
            return min(int(digits), 21600)
    return DEFAULT_TIMEOUT


def _append(rec: dict) -> None:
    with open(LEDGER, "a", encoding="utf-8", newline="") as fh:
        fh.write(json.dumps(rec) + "\n")
        fh.flush()
        os.fsync(fh.fileno())


def _claim(job: Path) -> Path:
    """Rename into running\\ BEFORE executing. The rename is the claim - it is
    atomic on one volume, so two overlapping ticks cannot both take the job."""
    dst = RUNNING / job.name
    if dst.exists():
        dst = RUNNING / f"{job.stem}__{int(time.time())}{job.suffix}"
    job.rename(dst)
    return dst


def report_stale() -> list:
    """A job still in running\\ long after its ceiling is REPORTED, never silently
    retried. Re-running a job whose side effects already happened is worse than
    leaving it visible."""
    out = []
    now = time.time()
    for p in RUNNING.glob("*"):
        if p.is_file() and now - p.stat().st_mtime > STALE_RUNNING_SECS:
            out.append(p)
    return out


def tick(quiet: bool = False) -> int:
    _dirs()
    for p in report_stale():
        msg = (f"STALE: {p.name} has been in running\\ for "
               f"{(time.time() - p.stat().st_mtime) / 3600:.1f} h - NOT retried. "
               f"Its side effects may already have happened.")
        if not quiet:
            print("  " + msg)
        _append({"t": int(time.time()), "event": "stale", "job": p.name, "detail": msg})

    jobs = sorted([p for p in PENDING.glob("*")
                   if p.is_file() and p.suffix.lower() in RUNNABLE
                   and not _is_helper(p)])
    if not jobs:
        return 0

    ran = 0
    for job in jobs:
        if not _cmd_for(job):
            continue
        claimed = _claim(job)
        # 🔴 BUILD THE COMMAND FROM THE CLAIMED PATH, NOT THE ORIGINAL.
        # First version resolved the command BEFORE the rename, so cmd was handed a
        # path that no longer existed and every job returned rc=1 in 0.1 s -
        # including the one that was supposed to SUCCEED. The selftest caught it and
        # refused to certify the runner, which is the only reason it was not
        # scheduled into service broken. Verifying a path is not verifying the path
        # you are about to use.
        cmd = _cmd_for(claimed)
        log = LOGS / f"{claimed.stem}__{time.strftime('%Y-%m-%dT%H-%M-%S')}.log"
        started = time.time()
        # RUNNING is written BEFORE the work, so a crash mid-job is distinguishable
        # from a job that never started. bts_deadline.py's rule.
        log.write_text(f"RUNNING {claimed.name}\nstarted {time.ctime(started)}\n"
                       f"cmd {cmd}\n\n", encoding="utf-8")
        _append({"t": int(started), "event": "start", "job": claimed.name,
                 "log": log.name})
        rc = None
        timed_out = False
        try:
            # 🔴 UTF-8, ALWAYS. Measured 2026-08-11: rail_check, bts_drive_health,
            # bench_drive and bts_kdash_feed ALL died with
            #   UnicodeEncodeError: 'charmap' codec can't encode '\U0001f534'
            # because they print 🔴 and box-drawing characters, and Windows falls
            # back to cp1252 the moment stdout is REDIRECTED. Run by hand in a
            # console they work; run by a scheduler they crash.
            # ==> The monitor worked whenever anyone was watching it.
            # CLAUDE.md already carries "NO EMOJI IN A .bat" - the rule was written
            # for cmd and never carried across to the Python tools' own stdout.
            env = dict(os.environ, PYTHONUTF8="1", PYTHONIOENCODING="utf-8")
            r = subprocess.run(cmd, capture_output=True, text=True,
                               errors="replace", timeout=_timeout_for(claimed),
                               cwd=str(QUEUE_ROOT), env=env)
            rc = r.returncode
            body = (r.stdout or "") + (("\n--- stderr ---\n" + r.stderr) if r.stderr else "")
        except subprocess.TimeoutExpired as e:
            timed_out = True
            body = ((e.stdout or "") if isinstance(e.stdout, str) else "") + \
                   f"\n\nRED - TIMED OUT after {_timeout_for(claimed)} s"
        except Exception as e:
            body = f"\n\nRED - RUNNER ERROR: {e}"
        elapsed = time.time() - started
        # PLM-44: three outcomes, and the verdict says which in words.
        if timed_out:
            verdict = "TIMED OUT"
        elif rc == RC_CLEAN:
            verdict = "OK"
        elif rc == RC_FINDINGS:
            verdict = "FINDINGS rc=2 — the job RAN and REPORTED something. Not a failure."
        else:
            verdict = f"FAILED rc={rc}"
        with open(log, "a", encoding="utf-8", newline="") as fh:
            fh.write(body or "")
            fh.write(f"\n\n{verdict}  elapsed {elapsed:.1f}s\n")
        if timed_out:
            dest = FAILED
        elif rc == RC_CLEAN:
            dest = DONE
        elif rc == RC_FINDINGS:
            dest = FINDINGS
        else:
            dest = FAILED
        target = dest / claimed.name
        if target.exists():
            # A collision must never leave the job stranded in running\, where it
            # then reports as STALE forever and looks like a hung process. Measured:
            # the first run left `_selftest_ok.bat` in BOTH running\ and failed\.
            target = dest / f"{claimed.stem}__{int(time.time())}{claimed.suffix}"
        try:
            claimed.rename(target)
        except OSError as e:
            _append({"t": int(time.time()), "event": "move_failed",
                     "job": claimed.name, "detail": str(e)})
        _append({"t": int(time.time()), "event": "end", "job": claimed.name,
                 "rc": rc, "timed_out": timed_out, "elapsed": round(elapsed, 1),
                 "verdict": verdict, "log": log.name})
        if not quiet:
            print(f"  {verdict:<14} {claimed.name}  {elapsed:.1f}s  -> {log.name}")
        ran += 1
    return ran


def status() -> None:
    _dirs()
    for label, d in (("queued", PENDING), ("running", RUNNING),
                     ("done", DONE), ("failed", FAILED)):
        if d is PENDING:
            items = [p.name for p in d.glob("*")
                     if p.is_file() and p.suffix.lower() in RUNNABLE
                     and not _is_helper(p)]
        else:
            items = [p.name for p in d.glob("*") if p.is_file()]
        print(f"  {label:<8} {len(items):>3}   {', '.join(items[:6])}"
              + (" ..." if len(items) > 6 else ""))
    # Helpers are PRINTED, never silently dropped. A file sitting in the queue that the
    # runner has quietly decided to ignore must be visible, or "it never ran" and "it was
    # skipped on purpose" look identical from the outside.
    helpers = [p.name for p in PENDING.glob("*") if p.is_file() and _is_helper(p)]
    if helpers:
        print(f"  {'helpers':<8} {len(helpers):>3}   {', '.join(helpers[:6])}"
              + (" ..." if len(helpers) > 6 else "")
              + "   (skipped by design - supporting files, not jobs)")
    stale = report_stale()
    if stale:
        print(f"  !! {len(stale)} STALE job(s): {', '.join(p.name for p in stale)}")
    if LEDGER.exists():
        lines = LEDGER.read_text(encoding="utf-8", errors="replace").splitlines()
        print(f"\n  last 5 ledger events ({len(lines)} total):")
        for ln in lines[-5:]:
            print("   ", ln[:160])
    else:
        print("\n  ledger EMPTY - the runner has never executed anything. If a task is")
        print("  installed and this stays empty, the TASK is the defect, not the queue.")


def selftest() -> int:
    """NEGATIVE CONTROL. A runner that has only ever been shown to succeed is not a
    runner - the whole point is that failures and timeouts are VISIBLE."""
    _dirs()
    # NOTE THE NAMES. These plants used to be `_selftest_*.bat`, and the `_` skip added
    # 2026-08-11 would have made this test certify a runner that ran nothing at all - the
    # jobs would have been skipped and every assertion below would have failed for the
    # wrong reason. A convention and the test that proves it have to move together.
    ok_job = PENDING / "selftest_ok.bat"
    bad_job = PENDING / "selftest_fail.bat"
    find_job = PENDING / "selftest_findings.bat"
    helper = PENDING / "_selftest_helper.py"
    ok_job.write_text("@echo off\r\necho selftest ok\r\nexit /b 0\r\n", encoding="ascii")
    bad_job.write_text("@echo off\r\necho selftest deliberate failure\r\nexit /b 7\r\n",
                       encoding="ascii")
    # PLM-44: a checker that FOUND something must not be filed as a broken job.
    find_job.write_text("@echo off\r\necho selftest reports findings\r\nexit /b 2\r\n",
                        encoding="ascii")
    # The helper is a REAL, RUNNABLE .py. If the skip is not working it will be claimed,
    # renamed into running\ and executed - which is exactly what happened to
    # _tidyup2_checks.py. Planting an unrunnable file would prove nothing.
    helper.write_text("print('this helper must never be executed by the runner')\n",
                      encoding="ascii")
    tick(quiet=True)
    good = (DONE / "selftest_ok.bat").exists()
    bad = (FAILED / "selftest_fail.bat").exists()
    logs = list(LOGS.glob("selftest_*"))
    has_rc7 = any("FAILED rc=7" in p.read_text(encoding="utf-8", errors="replace")
                  for p in logs)
    # The finding must land in done\findings\ and NOT in failed\.
    found_ok = ((FINDINGS / "selftest_findings.bat").exists()
                and not (FAILED / "selftest_findings.bat").exists())
    found_worded = any("FINDINGS rc=2" in p.read_text(encoding="utf-8", errors="replace")
                       for p in logs)
    # 🔴 THE NEW CONTROL. The helper must be exactly where it was put: still in the queue
    # root, NOT in running\, NOT in done\, and with no log of its own.
    helper_untouched = (helper.exists()
                        and not (RUNNING / helper.name).exists()
                        and not (DONE / helper.name).exists()
                        and not (FAILED / helper.name).exists()
                        and not list(LOGS.glob("_selftest_helper__*")))
    print(f"  {'OK  ' if good else 'FAIL'}  a succeeding job lands in done\\")
    print(f"  {'OK  ' if bad else 'FAIL'}  a FAILING job lands in failed\\, not done\\")
    print(f"  {'OK  ' if has_rc7 else 'FAIL'}  the failure's exit code is in its log")
    print(f"  {'OK  ' if helper_untouched else 'FAIL'}  a _-prefixed HELPER is left alone "
          f"(not claimed, not run, not moved)")
    print(f"  {'OK  ' if found_ok else 'FAIL'}  a job reporting FINDINGS (rc=2) lands in "
          f"done\\findings\\, NOT in failed\\")
    print(f"  {'OK  ' if found_worded else 'FAIL'}  and its log says FINDINGS in words, "
          f"not just a number")
    for p in (list(logs) + list(LOGS.glob("_selftest_helper__*"))
              + [DONE / "selftest_ok.bat", FAILED / "selftest_fail.bat", helper,
                 FINDINGS / "selftest_findings.bat", FAILED / "selftest_findings.bat",
                 RUNNING / helper.name, DONE / helper.name, FAILED / helper.name]):
        try:
            p.unlink()
        except OSError:
            pass
    good_all = (good and bad and has_rc7 and helper_untouched and found_ok
                and found_worded)
    print("SELFTEST PASS - success, failure, FINDINGS, the exit code and the helper skip "
          "are all visible and distinguishable."
          if good_all else "SELFTEST FAIL - do not trust this runner.")
    return 0 if good_all else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--once", action="store_true", help="one tick (what the task calls)")
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if a.status:
        status()
        return 0
    n = tick()
    if not a.once and n == 0:
        print("  nothing queued")
    return 0


if __name__ == "__main__":
    sys.exit(main())
