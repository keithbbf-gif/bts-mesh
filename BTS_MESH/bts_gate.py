"""
bts_gate.py — BUILD-5. The NEEDS_INPUT gate: pause, persist, resume on a human decision.

SGH's mine ranked LangGraph `interrupt()` #5: "pause agent execution and wait for
external/human input with state preserved."

ENGINEERING CALL (deliberate, and worth stating): we lift the PATTERN, not the
DEPENDENCY. LangGraph is a graph-execution framework; adopting it to gate a file-based
bus would mean restructuring the entire mesh around its runtime to get a behaviour that
is ~40 lines here. The mesh already has durable state (the append-only log) and a
NEEDS_INPUT signal type. What was missing was the *gate itself* — something that
actually STOPS work and survives a restart. That is what this is.

The pattern, faithfully:
  interrupt()  -> raise_gate()   : persist the question, halt the mesh
  (human)      -> answer_gate()  : record Keith's decision
  resume       -> is_open()      : blocked work checks before proceeding, and can
                                   pick up exactly where it left off

Durable: state lives in BTS_GATE.json, so a gate survives a crash/restart. That is the
half of interrupt() that actually matters — an in-memory pause is worthless.
"""
from __future__ import annotations

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import bts_bus  # noqa: E402

GATE_PATH = os.path.join(HERE, "BTS_GATE.json")
LOG_PATH = os.path.join(HERE, "BTS_SIGNAL.log")


def _load() -> dict:
    if not os.path.exists(GATE_PATH):
        return {"gates": []}
    try:
        with open(GATE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {"gates": []}


def _save(state: dict) -> None:
    # Atomic — a reader must never see a half-written gate file.
    bts_bus.atomic_write(GATE_PATH, json.dumps(state, indent=2))


def raise_gate(agent: str, question: str, path: str | None = None) -> dict:
    """interrupt(). Persist the blocking question and HALT. Idempotent: re-raising the
    same open question does not duplicate it."""
    state = _load()
    for g in state["gates"]:
        if g["status"] == "open" and g["question"] == question and g["agent"] == agent:
            return g  # already blocking on exactly this
    gate = {
        "id": f"gate-{len(state['gates']) + 1}",
        "agent": (agent or "?").upper(),
        "question": question,
        "path": path,
        "status": "open",
        "answer": None,
        "raised_ts": bts_bus.utc_now(),
        "answered_ts": None,
    }
    state["gates"].append(gate)
    _save(state)
    return gate


def open_gates() -> list:
    return [g for g in _load()["gates"] if g["status"] == "open"]


def is_open() -> bool:
    """Blocked work checks this before proceeding. True = the mesh must NOT advance."""
    return bool(open_gates())


def answer_gate(gate_id: str, answer: str, agent: str = "KEITH") -> dict:
    """The human decision lands. Resolve the gate and announce it on the bus so any
    node waiting on it can resume."""
    state = _load()
    for g in state["gates"]:
        if g["id"] == gate_id and g["status"] == "open":
            g["status"] = "answered"
            g["answer"] = answer
            g["answered_ts"] = bts_bus.utc_now()
            g["answered_by"] = agent
            _save(state)
            try:
                env = bts_bus.make_envelope(
                    "STATUS",
                    note=f"gate {gate_id} answered: {answer[:80]}",
                )
                bts_bus.append_signal(LOG_PATH, "CLA", env)
            except Exception:
                pass  # the gate is resolved either way; the bus note is a courtesy
            return g
    raise KeyError(f"no open gate {gate_id!r}")


def main():
    import argparse

    ap = argparse.ArgumentParser(description="BTS NEEDS_INPUT gate")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("list", help="show open gates")

    r = sub.add_parser("raise", help="raise a gate (interrupt)")
    r.add_argument("agent")
    r.add_argument("question")

    a = sub.add_parser("answer", help="answer a gate (resume)")
    a.add_argument("gate_id")
    a.add_argument("answer")

    args = ap.parse_args()

    if args.cmd == "list":
        gates = open_gates()
        if not gates:
            print("no open gates — mesh is clear to proceed")
        for g in gates:
            print(f"  {g['id']}  [{g['agent']}]  {g['question']}")
        return 0
    if args.cmd == "raise":
        g = raise_gate(args.agent, args.question)
        print(f"gate raised: {g['id']} — mesh HALTED pending a human decision")
        return 0
    if args.cmd == "answer":
        g = answer_gate(args.gate_id, args.answer)
        print(f"gate {g['id']} answered -> mesh may resume")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
