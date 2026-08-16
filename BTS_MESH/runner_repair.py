r"""
runner_repair.py — fix the BTS Queue Runner's MECHANISM, not its symptom. 2026-08-16.

MEASURED, LIVE, TONIGHT: last queue log 02:32. A job was dropped into V:\Ai\_queue at 03:26 and
sat UNCLAIMED for 58 minutes. This is the documented intermittency happening in front of us:
    "Ran to 23:32 · 43 minutes with two jobs unclaimed · woke 00:15 · stalled by 00:21 ..."

🔴 THREE HYPOTHESES ARE ALREADY DEAD. Do not reach for a fourth.
   1. Stuck instance   — Status read Ready throughout. Dead.
   2. Power condition  — BatteryChargeStatus=NoSystemBattery. This is a desktop on AC; the
                         "Stop On Battery Mode" flag CANNOT fire. Dead.
   3. "A UPS on battery" — THERE IS NO UPS. In this workspace UPS is Ultraviolet Photoelectron
                         Spectroscopy, the dissertation. That whole causal chain came from
                         misreading an acronym and reached five artifacts. S-146.

🔴 AND IT CANNOT BE DIAGNOSED AT ALL YET — THAT IS THE ACTUAL FINDING.
   Microsoft-Windows-TaskScheduler/Operational is DISABLED, so Windows kept NO per-run history.
   That log is the ONLY thing separating "the scheduler never fired" from "it fired and bts_runner
   ate the tick". An absent log is not an absent problem.
   The 2026-08-13 attempt to enable it returned rc=5, Access is denied. It has been waiting for
   elevation ever since. THAT IS WHY THIS SCRIPT MUST RUN ELEVATED.

WHAT IT DOES, in order, and why each is necessary rather than hopeful:
   1. Enable the TaskScheduler Operational log  -> the NEXT stall becomes diagnosable.
   2. Set MultipleInstances = StopExisting      -> the durable change. `schtasks` CANNOT set this;
                                                   only the PowerShell ScheduledTasks module can,
                                                   which is why it has never been fixed.
   3. Kick the runner and drain the queue       -> clears the symptom NOW so tonight's work lands.
   4. Report the settings it actually read back -> assert the artifact, not the command's exit code
                                                   (C-29: exit codes lie in the direction of success).
"""
import os
import subprocess
import sys
import time

MESH = os.path.dirname(os.path.abspath(__file__))
RUNNER = os.path.join(MESH, "bts_runner.py")
TASK = "BTS Queue Runner"
LOG = "Microsoft-Windows-TaskScheduler/Operational"


def sh(args, timeout=180):
    try:
        p = subprocess.run(args, capture_output=True, timeout=timeout)
        return p.returncode, (p.stdout or b"").decode("utf-8", "replace") + \
                             (p.stderr or b"").decode("utf-8", "replace")
    except Exception as e:                                            # noqa: BLE001
        return 99, str(e)


def ps(script, timeout=180):
    return sh(["powershell", "-NoProfile", "-NonInteractive", "-Command", script], timeout)


def main() -> int:
    print("=" * 78)
    print("  BTS QUEUE RUNNER - MECHANISM REPAIR")
    print("=" * 78)

    rc, out = ps("([Security.Principal.WindowsPrincipal]"
                 "[Security.Principal.WindowsIdentity]::GetCurrent())"
                 ".IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)")
    elevated = "True" in out
    print("\n  elevated: " + str(elevated))
    if not elevated:
        print("  [!] NOT ELEVATED. Steps 1 and 2 will fail with Access is denied, exactly as they")
        print("      did on 2026-08-13. Close this and use the .bat, which self-elevates.")

    # ---- 1. the history log ------------------------------------------------------------------
    print("\n" + "-" * 78)
    print("  1. TASK SCHEDULER HISTORY LOG")
    print("-" * 78)
    rc, out = sh(["wevtutil", "sl", LOG, "/e:true"])
    print("  wevtutil sl /e:true -> rc=" + str(rc))
    if out.strip():
        print("  " + out.strip()[:300])
    # ASSERT THE ARTIFACT. rc=0 is not evidence the log is on.
    rc2, out2 = sh(["wevtutil", "gl", LOG])
    enabled = "enabled: true" in out2.lower()
    print("  read back: enabled=" + str(enabled))
    if enabled:
        print("  [OK] The next stall leaves evidence. This is the single most important line here -")
        print("       without it, 'the scheduler never fired' and 'the runner ate the tick' are")
        print("       indistinguishable, and three sessions have now guessed between them.")
    else:
        print("  [!] STILL DISABLED. Without elevation this cannot be set.")

    # ---- 2. the durable setting --------------------------------------------------------------
    print("\n" + "-" * 78)
    print("  2. MULTIPLE INSTANCES -> StopExisting   (the durable fix)")
    print("-" * 78)
    print("  schtasks cannot express this setting. That is why restarting the task has cleared the")
    print("  symptom before and left the mechanism untouched every time.")
    rc, out = ps(
        "$ErrorActionPreference='Stop';"
        "try{"
        "  $t = Get-ScheduledTask -TaskName '" + TASK + "';"
        "  $before = $t.Settings.MultipleInstances;"
        "  $t.Settings.MultipleInstances = 'StopExisting';"
        "  $t.Settings.ExecutionTimeLimit = 'PT30M';"
        "  $t.Settings.DisallowStartIfOnBatteries = $false;"
        "  $t.Settings.StopIfGoingOnBatteries = $false;"
        "  Set-ScheduledTask -InputObject $t | Out-Null;"
        "  $a = (Get-ScheduledTask -TaskName '" + TASK + "').Settings;"
        "  Write-Output ('BEFORE=' + $before);"
        "  Write-Output ('AFTER=' + $a.MultipleInstances);"
        "  Write-Output ('TimeLimit=' + $a.ExecutionTimeLimit);"
        "  Write-Output ('DisallowOnBatteries=' + $a.DisallowStartIfOnBatteries);"
        "  Write-Output ('StopIfOnBatteries=' + $a.StopIfGoingOnBatteries);"
        "}catch{ Write-Output ('ERR ' + $_.Exception.Message) }")
    print("  " + out.strip().replace("\n", "\n  ")[:900])
    if "AFTER=StopExisting" in out:
        print("\n  [OK] Durable. A tick that arrives while a previous run is still going will now")
        print("       replace it instead of being silently dropped.")
    else:
        print("\n  [!] NOT SET. Read the message above before trying anything else.")

    # ---- 3. current state, then kick ---------------------------------------------------------
    print("\n" + "-" * 78)
    print("  3. STATE, THEN KICK")
    print("-" * 78)
    rc, out = sh(["schtasks", "/Query", "/TN", TASK, "/FO", "LIST", "/V"])
    for line in out.splitlines():
        low = line.lower()
        if any(k in low for k in ("status:", "last run time:", "last result:", "next run time:",
                                  "scheduled task state:", "task to run:")):
            print("  " + line.strip()[:150])

    print("\n  running bts_runner --once, three times, to drain whatever is queued:")
    for i in range(3):
        rc, out = sh(["py", "-3.14", RUNNER, "--once"], timeout=900)
        head = (out.strip().splitlines() or ["(no output)"])[0][:120]
        print("    pass " + str(i + 1) + ": rc=" + str(rc) + "  " + head)
        time.sleep(2)

    rc, out = sh(["schtasks", "/Run", "/TN", TASK])
    print("\n  schtasks /Run -> rc=" + str(rc) + "  " + out.strip()[:160])

    # ---- 4. did the queue actually drain? ----------------------------------------------------
    print("\n" + "-" * 78)
    print("  4. IS THE QUEUE EMPTY?   (the only unambiguous signal)")
    print("-" * 78)
    q = r"V:\Ai\_queue"
    try:
        pend = [f for f in os.listdir(q)
                if f.lower().endswith((".py", ".bat", ".ps1")) and not f.startswith("_")]
        print("  unclaimed jobs in the queue root: " + str(len(pend)))
        for f in pend:
            print("    " + f)
        if not pend:
            print("  [OK] Nothing stranded.")
        else:
            print("  [!] Still stranded. The runner is not claiming. Now that the history log is on,")
            print("      the next stall can be read from Event Viewer instead of guessed at.")
    except Exception as e:                                            # noqa: BLE001
        print("  [!] " + str(e))

    print("\n" + "=" * 78)
    print("  A dead runner cannot report itself. The beacon that matters is QUEUED-AND-UNCLAIMED,")
    print("  which rail_check already carries - not the runner's own ledger, which is written only")
    print("  when a job runs and therefore makes idle and dead look identical.")
    print("=" * 78)
    return 0


if __name__ == "__main__":
    sys.exit(main())
