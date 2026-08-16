"""
bts_dymon.py  — the BTS mesh watcher.  (was bts_daemon.py)

Named for Socrates' daimonion: the inner voice that, by his account, NEVER told him what to do —
it only ever told him NO. That is exactly this component's job. It does not generate, it does not
decide, it does not agree. It watches the surfaces, and it says NO:
  - NO, that envelope is malformed  -> dead-letter it
  - NO, that file is a OneDrive placeholder stub, the bytes are not there
  - NO, that chunk's planted control was not caught, so the whole chunk is void
A mesh full of agreeable nodes is worthless. The dymon is the part that refuses.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import bts_bus            # noqa: E402
import bts_watcher        # noqa: E402

try:
    import bts_schemas
    _TYPED = True
except Exception:  # pragma: no cover
    _TYPED = False

LOG_PATH = os.path.join(HERE, "BTS_SIGNAL.log")
CURSOR_PATH = os.path.join(HERE, ".bts_daemon.cursor")
DEADLETTER_PATH = os.path.join(HERE, "BTS_DEADLETTER.log")

ME = "CLA"  # this daemon runs on the Cowork side; never eat our own signals


# ---------------------------------------------------------------- handlers

def on_new_output(rec):
    env = rec["env"]
    print(f"  -> NEW_OUTPUT_READY from {rec['agent']}: read {env.get('path')}")
    return {"action": "read_and_verify", "path": env.get("path")}


def on_task_complete(rec):
    print(f"  -> TASK_COMPLETE from {rec['agent']}: {rec['env'].get('note')}")
    return {"action": "advance_queue"}


def on_needs_input(rec):
    # The whole point of the LangGraph interrupt() pattern: STOP, persist, surface.
    env = rec["env"]
    print(f"  !! NEEDS_INPUT from {rec['agent']}: {env.get('note')}")
    try:
        import bts_gate
        bts_gate.raise_gate(rec["agent"], env.get("note", ""), env.get("path"))
        print("     (gate raised -> BTS_GATE.json; mesh will not proceed past this)")
    except Exception as e:
        print(f"     (could not raise gate: {e})")
    return {"action": "halt_and_surface"}


def on_question(rec):
    print(f"  -> QUESTION_FOR_YOU from {rec['agent']}: answer into {rec['env'].get('path')}")
    return {"action": "answer"}


def on_error(rec):
    print(f"  xx ERROR from {rec['agent']}: {rec['env'].get('note')}")
    return {"action": "dead_letter"}


def on_default(rec):
    print(f"  .. {rec['env'].get('type')} from {rec['agent']}: {rec['env'].get('note')}")
    return {"action": "log_only"}


HANDLERS = {
    "NEW_OUTPUT_READY": on_new_output,
    "TASK_COMPLETE": on_task_complete,
    "NEEDS_INPUT": on_needs_input,
    "QUESTION_FOR_YOU": on_question,
    "ERROR": on_error,
}


# ---------------------------------------------------------------- core

def dead_letter(raw, reason):
    with open(DEADLETTER_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps({"reason": str(reason), "raw": raw, "ts": bts_bus.utc_now()}) + "\n")


def drain(replay=False):
    """Read every NEW signal and dispatch it. Returns the list of results."""
    if replay and os.path.exists(CURSOR_PATH):
        os.remove(CURSOR_PATH)

    recs = bts_bus.read_new_signals(LOG_PATH, CURSOR_PATH, mine=ME)
    results = []
    for rec in recs:
        env = rec["env"]
        # Typed validation. A malformed envelope is dead-lettered, never dispatched.
        if _TYPED:
            try:
                bts_schemas.validate(env)
            except Exception as e:
                print(f"  xx INVALID envelope from {rec['agent']}: {e}")
                dead_letter(rec, e)
                results.append({"action": "dead_letter", "error": str(e)})
                continue
        handler = HANDLERS.get(env.get("type"), on_default)
        try:
            results.append(handler(rec))
        except Exception as e:  # a bad handler must not kill the daemon
            dead_letter(rec, e)
            results.append({"action": "dead_letter", "error": str(e)})
    return results


def main():
    ap = argparse.ArgumentParser(description="BTS event-driven bus daemon")
    ap.add_argument("--once", action="store_true", help="drain once and exit")
    ap.add_argument("--replay", action="store_true", help="re-read the log from the start")
    ap.add_argument("--timeout", type=float, default=None, help="stop after N seconds")
    args = ap.parse_args()

    print("=" * 60)
    print("BTS DAEMON — event-driven (watchdog). Poll latency 10min -> ~1s.")
    print(f"  log    : {LOG_PATH}")
    print(f"  cursor : {CURSOR_PATH}")
    print("=" * 60)

    print("[boot] draining backlog ...")
    res = drain(replay=args.replay)
    print(f"[boot] dispatched {len(res)} signal(s)")

    if args.once:
        return 0

    stop = threading.Event()

    def on_change(path, ev):
        if os.path.basename(path) != os.path.basename(LOG_PATH):
            return
        time.sleep(0.05)  # let the append settle
        out = drain()
        if out:
            print(f"[event] {ev} -> dispatched {len(out)} new signal(s)")

    # --- OS-sync surfaces: a file landing from Google Drive / OneDrive is an EVENT.
    # The sync client writes it to disk; watchdog fires; we pick it up in ~1s.
    # Note we do NOT trust arrival: a freshly-synced file can still be a placeholder
    # stub with no bytes (OneDrive Files On-D