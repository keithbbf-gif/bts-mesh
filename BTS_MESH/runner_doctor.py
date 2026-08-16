#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""runner_doctor.py - why did the queue runner stop, and start it again. 2026-08-11/12.

MEASURED 2026-08-12 00:14: `BTS Queue Runner` executed its last job at 23:32 and then
stopped. Two jobs sat unclaimed in V:\\Ai\\_queue\\ for six minutes, running\\ was empty,
and the ledger recorded nothing. **NOTHING REPORTED IT.**

THAT IS THE POINT, NOT THE OUTAGE
---------------------------------
The background lane closed PLM-25 on 2026-08-11 and immediately became load-bearing:
fourteen jobs ran through it in one session, and every verification this session performed
went through it. It has NO LIVENESS BEACON. A runner that stops looks exactly like a
runner with nothing to do - the ledger is quiet in both cases.

That is PLM-13, still open since 2026-07-30: *"a monitor that watches the monitors...
rail_check reports a monitor whose last write is older than its cadence."* The runner is
now the most load-bearing monitor in the mesh and it is not in that registry.

  ==> A QUEUE WITH WORK IN IT AND NO CLAIM ON IT IS THE SIGNAL. It costs one stat call.
      `stale_pending()` below is that check, and it needs no scheduler to run.

WHAT THIS DOES
    --check    report task state, last tick, and any job that has been waiting too long
    --start    ask the Windows scheduler to run the task now
    --install  re-register the task if it is gone entirely

⚠ `schtasks /change /tn ... /enable` and re-registration may require ELEVATION. If it
does, this prints the exact command rather than failing silently - Keith does elevation.
"""
from __future__ import annotations

import datetime as dt
import json
import pathlib
import re
import subprocess
import sys

QUEUE = pathlib.Path(r"V:\Ai\_queue")
LEDGER = QUEUE / "runner_ledger.jsonl"
RUNNING = QUEUE / "running"
TASK = "BTS Queue Runner"
RUNNER = pathlib.Path(r"V:\Research4\Ai\BTS_MESH\bts_runner.py")
PENDING_GRACE_S = 180          # 3 ticks. Longer than any legitimate scheduling jitter.


def _run(args):
    try:
        r = subprocess.run(args, capture_output=True, text=True, errors="replace",
                           timeout=60)
        return r.returncode, (r.stdout or "") + (r.stderr or "")
    except Exception as e:                                          # noqa: BLE001
        return 1, str(e)


def last_tick():
    if not LEDGER.exists():
        return None
    last = None
    for line in LEDGER.read_bytes().decode("utf-8", "replace").splitlines():
        if line.strip():
            try:
                last = json.loads(line)
            except ValueError:
                continue
    return last


def stale_pending():
    """Jobs sitting in the queue root with nothing claiming them.

    THIS IS THE LIVENESS CHECK THE RUNNER NEVER HAD. It does not ask the scheduler
    anything and it does not need the runner to be alive to work - which is the whole
    requirement, because a dead runner cannot report itself."""
    now = dt.datetime.now().timestamp()
    out = []
    for p in sorted(QUEUE.glob("*")):
        if p.is_file() and p.suffix.lower() in (".py", ".bat", ".cmd", ".ps1") \
                and not p.name.startswith("_"):
            waited = now - p.stat().st_mtime
            if waited > PENDING_GRACE_S:
                out.append((p.name, waited))
    return out


def check() -> int:
    print("=" * 78)
    print("  runner_doctor --check    %s" % dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("=" * 78)

    # 🔴 THE SLEEP HYPOTHESIS IS ALREADY RULED OUT, AND THAT MATTERS.
    # Measured 2026-08-12 00:14-01:02: the Cowork sandbox was reading and writing V:
    # continuously across every one of the stalls. That mount is served by this machine.
    # ==> THE MACHINE WAS AWAKE THE WHOLE TIME. This is not the box going to sleep after
    #     midnight; it is a per-minute task that is not firing per minute. Different
    #     problem, different fix, and the obvious guess was the wrong one.
    #
    # What that leaves, in order of how often it is the answer:
    #   1. AN INSTANCE IS STILL RUNNING. Task Scheduler's default multiple-instances rule
    #      is "Do not start a new instance." One hung pyw process blocks every subsequent
    #      tick until it exits - which produces exactly the observed shape: long silence,
    #      then a burst when it finally clears. `Status: Running` below IS this answer.
    #   2. A REPETITION DURATION THAT EXPIRED. "Repeat every 1 minute for a duration of
    #      1 hour" stops after an hour and waits for the next trigger.
    #   3. A CONDITION: only on AC power, only when idle, stop when going on battery.
    #   4. "Stop the task if it runs longer than" killing it mid-job.
    rc, out = _run(["schtasks", "/query", "/tn", TASK, "/fo", "LIST", "/v"])
    if rc == 0:
        wanted = ("status", "last run time", "last result", "next run time",
                  "scheduled task state", "task to run", "logon mode",
                  "repeat: every", "repeat: until: duration", "repeat: stop if still running",
                  "power management", "stop task if runs x hours and x mins",
                  "start in", "run as user")
        for line in out.splitlines():
            k = line.split(":")[0].strip().lower()
            if k in wanted or any(k.startswith(w.split(":")[0]) for w in wanted if ":" in w):
                print("  %s" % line.strip()[:130])
        low = out.lower()
        print()
        if "status:" in low and "running" in low.split("status:", 1)[1][:40]:
            print("  [RED] STATUS = RUNNING. That is almost certainly the whole answer:")
            print("     an instance is stuck, and the default multiple-instances rule is")
            print("     'do not start a new instance', so every tick since has been")
            print("     suppressed. Kill the stuck process, then set the rule to")
            print("     'Stop the existing instance' so one hang cannot mute the lane.")
        # 🔴 THE FIRST VERSION SEARCHED THE WHOLE BLOB FOR "disabled" AND CRIED WOLF.
        # `Repeat: Until: Duration: Disabled` and `Repeat: Stop If Still Running: Disabled`
        # are both NORMAL and both contain the word. It reported a healthy task as
        # disabled. Seventh false positive of this session's own checkers; the fix is the
        # same every time - match the FIELD, not the word.
        for line in out.splitlines():
            k, _, v = line.partition(":")
            k, v = k.strip().lower(), v.strip().lower()
            if k == "scheduled task state" and "disabled" in v:
                print("  [RED] THE TASK ITSELF IS DISABLED. Nothing else matters until it is on.")

        # THE TWO CONDITIONS THAT ACTUALLY EXPLAIN AN INTERMITTENT PER-MINUTE TASK.
        # Measured on this machine 2026-08-12: Status Ready, Last Result 0, repeating
        # every 1 minute with no end duration - i.e. HEALTHY RIGHT NOW - while the lane
        # had demonstrably gone quiet for 43 minutes overnight. A task that is fine when
        # you look at it and dead when you do not is a CONDITIONAL task.
        # 🔴 THE POWER-CONDITION HYPOTHESIS IS DEAD. Measured 2026-08-13:
        #      BatteryChargeStatus = NoSystemBattery
        #      Win32_Battery       = (nothing)
        #      Get-PnpDevice -Class Battery = (nothing)
        # This is a desktop on AC only. `Stop On Battery Mode` CANNOT FIRE, so the flag
        # in the task's settings is inert and unticking it changes nothing.
        #
        # ⚠ AND THE STORY THAT PRODUCED IT WAS FICTION FROM THE START. It rested on
        # reading `Judge-UPS.vbs` as an uninterruptible power supply. UPS HERE IS
        # ULTRAVIOLET PHOTOELECTRON SPECTROSCOPY - the dissertation. See ROLD\GLOSSARY.md.
        if "stop on battery mode" in low:
            print()
            print("  [note] The task carries 'Stop On Battery Mode, No Start On Batteries'.")
            print("         IT IS INERT ON THIS MACHINE - no battery exists (measured")
            print("         2026-08-13: NoSystemBattery). Not the cause. Do not chase it.")

        print()
        print("  [RED] CAUSE OF THE 2026-08-12 STALL: UNKNOWN.")
        print("     Three hypotheses are dead:")
        print("       1. stuck instance   - Status read Ready throughout.")
        print("       2. power condition  - no battery exists on this machine.")
        print("       3. a UPS on battery - THERE IS NO UPS. UPS here is ultraviolet")
        print("                             photoelectron spectroscopy (GLOSSARY.md).")
        # ASK WHETHER THE LOG IS ON. Do not print an instruction for work already
        # done - Keith enabled it 2026-08-13 12:31 and the previous version kept
        # telling him to. A tool that instructs must first CHECK.
        lrc, lout = _run(["wevtutil", "gl",
                          "Microsoft-Windows-TaskScheduler/Operational"])
        log_on = bool(re.search(r"enabled:\s*true", lout, re.I))
        if log_on:
            print("     [OK] TASK HISTORY IS ON. The next stall IS diagnosable:")
            print("          event 129 = launched - 100 = started - 102 = completed.")
            print("          Launches during a silence => the scheduler fired and")
            print("          bts_runner ate the ticks. None => the scheduler stopped.")
            print("          Nothing more to do here but WAIT for it to happen again.")
        else:
            print("     AND IT CANNOT BE DIAGNOSED YET, WHICH IS ITSELF THE FINDING:")
            print("       Microsoft-Windows-TaskScheduler/Operational is DISABLED, so")
            print("       Windows keeps no per-run history - the one thing separating")
            print("       'the scheduler never fired' from 'it fired and bts_runner ate")
            print("       the ticks'. From an ELEVATED prompt:")
            print("         wevtutil sl \"Microsoft-Windows-TaskScheduler/Operational\" /e:true")
            print("       An absent log is not an absent problem.")


def unstick() -> int:
    """End a stuck instance, then set the multiple-instances rule so it cannot mute again.

    `schtasks /end` stops a running instance. The durable fix is the rule itself: with
    "do not start a new instance" (the default), ONE hang silences the whole lane
    indefinitely and nothing reports it - which is the failure being fixed, not a
    hypothetical."""
    print("  ending any running instance of '%s'..." % TASK)
    rc, out = _run(["schtasks", "/end", "/tn", TASK])
    print("  /end rc=%s  %s" % (rc, out.strip()[:200]))
    print()
    print("  [!] THE DURABLE FIX IS THE MULTIPLE-INSTANCES RULE, and schtasks cannot set")
    print("    it - it is an XML property. Either re-register from XML, or set it once in")
    print("    Task Scheduler: the task -> Settings -> 'If the task is already running,")
    print("    then the following rule applies:' -> STOP THE EXISTING INSTANCE.")
    print("    Also check, on that same tab:")
    print("      - Conditions -> 'Start the task only if the computer is on AC power' OFF")
    print("      - Conditions -> 'Start the task only if the computer is idle' OFF")
    print("      - Settings   -> 'Stop the task if it runs longer than' -> 1 hour")
    print("      - Triggers   -> repetition duration = INDEFINITELY, not 1 day")
    return rc


def start() -> int:
    print("  asking the scheduler to run '%s' now..." % TASK)
    rc, out = _run(["schtasks", "/run", "/tn", TASK])
    print("  rc=%s  %s" % (rc, out.strip()[:300]))
    if rc != 0:
        print()
        print("  [RED] COULD NOT START IT. If this is an access error it needs ELEVATION,")
        print("     which is Keith's. The exact command, from an ADMIN prompt:")
        print()
        print('     schtasks /run /tn "%s"' % TASK)
        print()
        print("  If the task is GONE rather than stopped, re-register it:")
        print()
        print('     schtasks /create /tn "%s" /sc minute /mo 1 /f ^' % TASK)
        print('       /tr "pyw -3.14 \\"%s\\" --once"' % RUNNER)
        return 1
    return 0


def install() -> int:
    """Re-register from scratch. /f overwrites, so this is idempotent."""
    cmd = ["schtasks", "/create", "/tn", TASK, "/sc", "minute", "/mo", "1", "/f",
           "/tr", 'pyw -3.14 "%s" --once' % RUNNER]
    print("  " + " ".join(cmd))
    rc, out = _run(cmd)
    print("  rc=%s  %s" % (rc, out.strip()[:300]))
    return rc


if __name__ == "__main__":
    if "--unstick" in sys.argv:
        sys.exit(unstick())
    if "--start" in sys.argv:
        sys.exit(start())
    if "--install" in sys.argv:
        sys.exit(install())
    sys.exit(check())
