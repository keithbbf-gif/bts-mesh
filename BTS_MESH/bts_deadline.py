#!/usr/bin/env python3
"""bts_deadline.py — run work under a deadline and make a TIMEOUT LOUD.  2026-07-31

    "Or set a trigger to time out at 44 seconds and set a red flag?"   — Keith, 2026-07-31

THE PROBLEM THIS SOLVES, measured twice on 2026-07-30
-----------------------------------------------------
A Cowork bash call is capped at **45,000 ms**, and that cap is in the tool definition — it cannot be
raised. Worse, **background processes do not survive between calls** (`nohup` and `setsid nohup`
both tested; both died silently). So a node call that runs long is killed mid-flight and leaves
behind an output file that is EMPTY or HALF-WRITTEN — and an empty file is indistinguishable from a
call that failed, or from a node that had nothing to say. Two SGH returns were lost that way, and
the first was misread as "the node returned a preamble and stopped".

**A truncated run that looks like a completed one is the whole failure.** The fix is not more time.
It is to guarantee that running out of time SAYS SO, in the output, where the reader will look.

WHAT IT GUARANTEES
  * the output file is written **first**, marked `RUNNING`, before the work starts
  * if the work finishes in time, the file is replaced with the real result marked `OK`
  * if the deadline passes, the file is left marked **`RED — TIMED OUT`** with the elapsed time
  * so **no possible outcome leaves a silent empty file**

DEFAULT DEADLINE = 44 s, deliberately one second inside the 45 s cap: we want OUR marker on disk,
not the harness's kill with nothing written.

USAGE
    from bts_deadline import guarded
    guarded(out_path, lambda: bts_sgh.ask(prompt), label="SGH survey")

NEGATIVE CONTROL — a guard never shown to fire is not a guard:
    python bts_deadline.py --selftest
runs work that deliberately overruns and asserts the file says TIMED OUT, then runs work that
finishes and asserts the file says OK.
"""
from __future__ import annotations

import os
import sys
import threading
import time

HARD_CAP_MS = 45_000          # the harness limit. Not ours to change.
DEFAULT_DEADLINE = 44.0       # one second inside it, on purpose.


def _write(path: str, text: str) -> None:
    # newline="" so Windows text mode cannot rewrite the bytes (SCARS S-59 / S-90)
    d = os.path.dirname(path)
    if d:
        os.makedirs(d, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write(text)


def guarded(out_path: str, work, label: str = "", deadline: float = DEFAULT_DEADLINE,
            header: str = "") -> dict:
    """Run `work()` under `deadline` seconds. The file at out_path ALWAYS ends up telling the truth.

    Returns {"ok": bool, "timed_out": bool, "secs": float, "result": <whatever work returned or None>}
    ⚠ A timed-out worker thread is abandoned, not killed — Python cannot safely kill a thread. The
    guarantee here is about the RECORD, not about reclaiming the process. Say so plainly rather than
    implying a clean cancel.
    """
    started = time.time()
    _write(out_path, f"{header}\nSTATUS: RUNNING — started {time.strftime('%Y-%m-%d %H:%M:%S')}"
                     f"\nlabel: {label}\ndeadline: {deadline:.0f}s\n")
    box: dict = {}

    def runner():
        try:
            box["result"] = work()
        except Exception as e:                       # noqa: BLE001
            box["error"] = f"{type(e).__name__}: {e}"

    th = threading.Thread(target=runner, daemon=True)
    th.start()
    th.join(timeout=deadline)
    secs = time.time() - started

    if th.is_alive():
        _write(out_path,
               f"{header}\n"
               f"STATUS: **RED - TIMED OUT** after {secs:.1f}s (deadline {deadline:.0f}s)\n"
               f"label: {label}\n\n"
               f"The work did not finish inside the {HARD_CAP_MS/1000:.0f}s harness cap. This file is\n"
               f"a MARKER, not a result. Nothing here was returned by the worker.\n"
               f"Split the work, run it natively in CoW (no cap), or make it resumable.\n"
               f"NOTE: the worker thread was abandoned, not killed - Python cannot safely kill one.\n")
        return {"ok": False, "timed_out": True, "secs": secs, "result": None}

    if "error" in box:
        _write(out_path, f"{header}\nSTATUS: **RED - FAILED** after {secs:.1f}s\nlabel: {label}\n\n"
                         f"{box['error']}\n")
        return {"ok": False, "timed_out": False, "secs": secs, "result": None}

    res = box.get("result")
    _write(out_path, f"{header}\nSTATUS: OK — {secs:.1f}s\nlabel: {label}\n\n{res}\n")
    return {"ok": True, "timed_out": False, "secs": secs, "result": res}


def selftest() -> int:
    import tempfile
    d = tempfile.mkdtemp(prefix="deadline_")
    slow, fast = os.path.join(d, "slow.md"), os.path.join(d, "fast.md")

    r1 = guarded(slow, lambda: time.sleep(3) or "never seen", label="overrun", deadline=1.0)
    t1 = open(slow, encoding="utf-8").read()
    r2 = guarded(fast, lambda: "finished in time", label="quick", deadline=5.0)
    t2 = open(fast, encoding="utf-8").read()

    ok1 = r1["timed_out"] and "TIMED OUT" in t1 and "never seen" not in t1
    ok2 = r2["ok"] and "STATUS: OK" in t2 and "finished in time" in t2
    print("  overrun -> file says TIMED OUT, no partial result :", "OK" if ok1 else "FAIL")
    print("  in-time -> file says OK and carries the result    :", "OK" if ok2 else "FAIL")
    import shutil; shutil.rmtree(d, ignore_errors=True)
    good = ok1 and ok2
    print("SELFTEST PASS — a timeout can no longer look like an empty answer."
          if good else "SELFTEST FAIL — do not rely on this guard.")
    return 0 if good else 1


if __name__ == "__main__":
    sys.exit(selftest() if "--selftest" in sys.argv else (print(__doc__) or 0))
