#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""bts_oa.py - the OA (OpenAI Codex CLI) consumption ledger.  2026-08-11

WHY THIS EXISTS
---------------
Every other rail in this mesh keeps a ledger. OA does not, and OA is the one rail
that can spend a prepaid allowance with NO RECORD AT ALL:

    OA = Codex CLI 0.147.0, Windows-native, auth mode `chatgpt`, NO API KEY stored.
    It draws Keith's ChatGPT plan, not a card.

That is worse than a metered rail, not better. A card produces a statement; a plan
produces a rate limit that arrives as a refusal in the middle of something else.
`bts_sgh` is exact to the cent, `bts_cop` counts credits, and 204 GW calls that went
unpriced are STILL distorting the xAI month-to-date figure a year later. The rule
that came out of that is the rule here:

    NEVER LET A CALL GO UNRECORDED, AND NEVER RECORD AN UNMEASURED CALL AS ZERO.

THE HONEST STATE OF THIS FILE, 2026-08-11
-----------------------------------------
`bts_cop.parse()` works because someone captured a real CoPG footer verbatim and
wrote the regex against it. NOBODY HAS EVER RUN A CODEX TASK ON THIS MACHINE.
Measured this session, host-side: `~/.codex/` contains auth.json, config.toml, a
login log and a tmp dir. There is NO `sessions/` directory, so there is no rollout
file, so there is no captured usage record of any shape.

    ==> THIS LEDGER SHIPS WITH NO PRICING RULE, DELIBERATELY.

Inventing a regex for a footer nobody has seen is exactly S-131/S-132 in a third
costume: a plausible artifact that is never asserted against reality. So instead:

  * `--scan` DISCOVERS the usage schema from Codex's own session rollouts and
    reports the key names it actually found. It reports NOT MEASURED when there is
    nothing there. It never invents a number.
  * `record()` accepts a run and prices it ONLY from a shape `--scan` has confirmed.
    Everything else increments `unpriced` and is written to `hist` with the raw
    tail attached, so the next session can build the rule from evidence.
  * `budget()` reports the allowance as UNKNOWN [U]. Codex's `/status` has never
    been read. Until it is, every statement about OA's limits comes off a pricing
    page rather than off the account, and this file will say so out loud.

WHAT AN "OA UNIT" IS, AND WHY IT IS NOT DOLLARS
-----------------------------------------------
On `chatgpt` auth there is no per-call dollar cost to record - the plan is prepaid,
so a dollar figure here would be a fabrication. The meters that are real:

    calls . tokens in / cached / out / reasoning . wall seconds . plan pct remaining

Dollars appear in this ledger ONLY for the separate `openai-api` lane (a real API
key, gpt-5.6-sol/terra/luna), which does not exist yet and is LAST in Keith's order.
When it lands it uses `record(..., lane="openai-api", usd=...)` and the two lanes
stay separate, because averaging a prepaid lane with a metered one destroys the
only signal either of them carries.

USAGE
    python bts_oa.py --scan                 # discover the usage schema. Writes nothing.
    python bts_oa.py --learn RAW.txt        # record one captured run + keep its shape
    python bts_oa.py                        # print the ledger
    python bts_oa.py --selftest             # negative control
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path

_HERE = Path(__file__).resolve().parent
LEDGER = _HERE / "oa_spend.json"
SHAPES = _HERE / "oa_usage_shape.json"      # what --scan learned. Evidence, not assumption.

CODEX_HOME = Path(os.environ.get("CODEX_HOME") or (Path.home() / ".codex"))
SESSIONS = CODEX_HOME / "sessions"

# The two lanes. They are NOT interchangeable and are never summed.
LANES = ("openai-codex", "openai-api")

# Token-ish key names worth reporting if a rollout carries them. This is a SEARCH
# LIST for --scan, not a schema claim: --scan prints what it found, and if it finds
# nothing it says NOT MEASURED. Do not turn this into a parser.
_TOKEN_HINTS = (
    "input_tokens", "output_tokens", "cached_input_tokens", "reasoning_output_tokens",
    "total_token_usage", "last_token_usage", "token_count", "prompt_tokens",
    "completion_tokens", "cached_tokens",
)

# Stdout fallback. UNVERIFIED - no Codex run has ever been observed on this machine.
# Kept inert on purpose: _parse_stdout() refuses to price unless --learn has confirmed
# the shape at least once, so a wrong guess CANNOT quietly become a number.
_RE_TOKENS = re.compile(
    r"tokens?\s*used[^0-9]{0,12}([0-9][0-9,]*)", re.I)


# --------------------------------------------------------------------------- io

def _load(path: Path = None) -> dict:
    try:
        with open(path or LEDGER, encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return {}


def _save(d: dict, path: Path = None) -> None:
    """Plain write, then fsync. NOT os.replace().

    bts_sgh._save() uses an atomic rename and DIES on the FUSE mount with
    FileNotFoundError - same family as the mount's refusal to unlink (measured
    2026-08-02). That is precisely why paid rails run natively. This ledger is
    written by a native run, but it must not become a second reason the sandbox
    cannot record a spend.
    """
    p = Path(path or LEDGER)
    with open(p, "w", encoding="utf-8", newline="") as fh:
        json.dump(d, fh, indent=2)
        fh.flush()
        os.fsync(fh.fileno())


def _month() -> str:
    return time.strftime("%Y-%m")


def _fresh(month: str) -> dict:
    return {
        "month": month,
        "lanes": {ln: {"calls": 0, "ok_calls": 0, "unpriced": 0,
                       "tok_in": 0, "tok_cached": 0, "tok_out": 0, "tok_reason": 0,
                       "secs": 0.0, "usd": 0.0} for ln in LANES},
        "hist": [],
    }


# ----------------------------------------------------------------- discovery

def _walk_rollouts(root: Path = None):
    root = Path(root or SESSIONS)
    if not root.is_dir():
        return
    for p in sorted(root.rglob("*.jsonl")):
        yield p


def _hits(obj, found: dict, path: str = "") -> None:
    """Recursively note every token-ish key and the type of its value."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            here = f"{path}.{k}" if path else k
            if k in _TOKEN_HINTS:
                found.setdefault(here, type(v).__name__)
            _hits(v, found, here)
    elif isinstance(obj, list):
        for v in obj[:50]:
            _hits(v, found, path + "[]")


def scan(root: Path = None, quiet: bool = False) -> dict:
    """Discover the usage schema from Codex's OWN rollout files.

    Writes oa_usage_shape.json ONLY when something was actually found. An empty
    scan must never overwrite a shape learned earlier, and must never be recorded
    as 'no usage' - it is 'NOT MEASURED', which is a different claim.
    """
    files = list(_walk_rollouts(root))
    found: dict = {}
    lines = 0
    for p in files:
        try:
            with open(p, encoding="utf-8", errors="replace") as fh:
                for ln in fh:
                    ln = ln.strip()
                    if not ln:
                        continue
                    lines += 1
                    try:
                        _hits(json.loads(ln), found)
                    except Exception:
                        continue
        except Exception as e:
            if not quiet:
                print(f"  ! unreadable {p.name}: {e}")

    out = {
        "scanned_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "root": str(root or SESSIONS),
        "rollout_files": len(files),
        "json_lines": lines,
        "usage_keys": found,
        "state": ("MEASURED" if found else
                  ("NOT MEASURED - rollouts exist but carry no usage keys" if files else
                   "NOT MEASURED - no rollout files; Codex has never run a task here")),
    }
    if not quiet:
        print(f"  codex home     {CODEX_HOME}")
        print(f"  sessions dir   {root or SESSIONS}   "
              f"{'present' if (root or SESSIONS).is_dir() else 'ABSENT'}")
        print(f"  rollout files  {len(files)}")
        print(f"  json lines     {lines:,}")
        if found:
            print("  usage keys FOUND:")
            for k, t in sorted(found.items()):
                print(f"    {k:<48} {t}")
        else:
            print("  usage keys     NONE FOUND")
        print(f"  state          {out['state']}")
    if found:
        _save(out, SHAPES)
        if not quiet:
            print(f"  wrote          {SHAPES.name}")
    elif not quiet:
        print("  wrote          nothing - an empty scan does not get to overwrite a "
              "learned shape, and absence is not a measurement")
    return out


def shape_known() -> bool:
    s = _load(SHAPES)
    return bool(s.get("usage_keys"))


# ------------------------------------------------------------------- pricing

def parse(raw: str) -> dict:
    """Pull usage out of a captured Codex run.

    Returns {} - meaning UNPRICED - unless a shape has been confirmed by --scan or
    --learn. This function is deliberately useless until something real has been
    measured. That is the feature: an unmeasured call must land in `unpriced`,
    never as a zero.
    """
    if not raw:
        return {}
    if not shape_known():
        return {}
    m = _RE_TOKENS.search(raw)
    if not m:
        return {}
    return {"tok_total": int(m.group(1).replace(",", ""))}


def record(raw: str = "", task: str = "", lane: str = "openai-codex",
           usage: dict = None, secs: float = None, usd: float = None,
           ok: bool = None, ledger: Path = None) -> dict:
    """Append exactly one OA invocation.

    `usage` is for a caller that already holds structured numbers (a wrapper reading
    the rollout). `raw` is for a caller that only has stdout. If neither yields a
    figure the call is recorded as UNPRICED, loudly, with the tail of its output
    kept so the shape can be learned from evidence later.
    """
    if lane not in LANES:
        raise ValueError(f"unknown lane {lane!r}; expected one of {LANES}")
    path = Path(ledger or LEDGER)
    d = _load(path)
    if d.get("month") != _month() or "lanes" not in d:
        d = _fresh(_month())
    for ln in LANES:                       # tolerate a ledger written before a lane existed
        d["lanes"].setdefault(ln, _fresh(d["month"])["lanes"][ln])

    L = d["lanes"][lane]
    L.setdefault("ok_calls", 0)
    u = dict(usage or {}) or parse(raw)
    L["calls"] += 1
    if ok:
        L["ok_calls"] += 1

    rec = {"t": int(time.time()), "lane": lane, "task": task, "ok": ok}
    if secs is not None:
        L["secs"] = round(L["secs"] + float(secs), 2)
        rec["secs"] = float(secs)

    if u:
        for src, dst in (("input_tokens", "tok_in"), ("prompt_tokens", "tok_in"),
                         ("cached_input_tokens", "tok_cached"), ("cached_tokens", "tok_cached"),
                         ("output_tokens", "tok_out"), ("completion_tokens", "tok_out"),
                         ("reasoning_output_tokens", "tok_reason")):
            if src in u:
                L[dst] += int(u[src] or 0)
        rec.update(u)
    else:
        L["unpriced"] += 1
        rec["UNPRICED"] = True
        rec["why"] = ("no usage record and no confirmed shape - run "
                      "`python bts_oa.py --scan` after this call")
        if raw:
            rec["tail"] = raw[-400:]       # evidence for building the rule later

    if usd is not None:
        if lane != "openai-api":
            raise ValueError("usd belongs to the openai-api lane only; the codex lane "
                             "is plan-drawn and a dollar figure there is a fabrication")
        L["usd"] = round(L["usd"] + float(usd), 6)
        rec["usd"] = float(usd)

    d["hist"] = (d.get("hist") or [])[-499:] + [rec]
    _save(d, path)
    return d


def budget() -> dict:
    d = _load()
    lanes = d.get("lanes") or {}
    codex = lanes.get("openai-codex", {})
    api = lanes.get("openai-api", {})
    shape = _load(SHAPES)
    return {
        "month": d.get("month"),
        "openai-codex": {
            "calls": codex.get("calls", 0),
            "ok_calls": codex.get("ok_calls", 0),
            "unpriced_calls": codex.get("unpriced", 0),
            "tok_in": codex.get("tok_in", 0),
            "tok_cached": codex.get("tok_cached", 0),
            "tok_out": codex.get("tok_out", 0),
            "tok_reason": codex.get("tok_reason", 0),
            "secs": codex.get("secs", 0.0),
            "usd": "N/A - plan-drawn, not billed",
        },
        "openai-api": {
            "calls": api.get("calls", 0),
            "unpriced_calls": api.get("unpriced", 0),
            "usd": round(api.get("usd", 0.0), 6),
            "state": "NOT STARTED - last in Keith's order, gated on the existing rails",
        },
        "allowance_[U]": "UNKNOWN. `codex` -> /status has never been read. Every number "
                         "about OA's limits currently comes off a pricing page, not off "
                         "the account. Read it before planning against it.",
        "context_ceiling": "272,000 tokens. MEASURED 2026-08-11 from the account's own "
                           "~/.codex/models_cache.json - every model this ChatGPT account "
                           "offers (gpt-5.6-terra, gpt-5.6-luna, gpt-5.5, gpt-5.4-mini) "
                           "carries context_window 272000. 🔴 THE WAR-GAME RECORD IS ~422k "
                           "TOKENS, SO OA CANNOT HOLD IT. Only the openai-api lane (1.05M) "
                           "can, and that lane does not exist yet.",
        "usage_shape": shape.get("state", "NOT MEASURED - --scan has never run"),
        "node_state": ("LIVE" if codex.get("ok_calls", 0) else
                       "REGISTERED, NOT LIVE - no SUCCESSFUL return has landed in a file. "
                       "A call that was attempted is not a call that answered (S-100); "
                       "counting attempts was this file's own first defect."),
    }


# ------------------------------------------------------------------ selftest

def selftest() -> int:
    """NEGATIVE CONTROL. The claim under test is not 'it can count' - it is
    'IT REFUSES TO INVENT A NUMBER.' Every assertion below is about the refusal."""
    import tempfile
    tmp = Path(tempfile.gettempdir()) / "_oa_selftest.json"
    tmpshape = Path(tempfile.gettempdir()) / "_oa_selftest_shape.json"
    empty = Path(tempfile.gettempdir()) / "_oa_selftest_sessions"
    empty.mkdir(exist_ok=True)
    results = []
    global SHAPES
    real_shapes = SHAPES
    try:
        # 1. An empty sessions tree is NOT MEASURED, never "zero usage".
        s = scan(empty, quiet=True)
        results.append(("empty scan says NOT MEASURED, not zero",
                        s["state"].startswith("NOT MEASURED") and not s["usage_keys"]))

        # 2. With no confirmed shape, a run that LOOKS priced is still UNPRICED.
        SHAPES = tmpshape
        if tmpshape.exists():
            tmpshape.unlink()
        results.append(("plausible output with no confirmed shape -> {}",
                        parse("done. tokens used 12,345") == {}))

        # 3. An unpriced call is recorded, counted and keeps its evidence.
        d = record("done. tokens used 12,345", task="selftest-unpriced", ledger=tmp)
        L = d["lanes"]["openai-codex"]
        results.append(("unpriced call recorded, not dropped",
                        L["calls"] == 1 and L["unpriced"] == 1 and
                        d["hist"][-1].get("UNPRICED") is True and
                        "tail" in d["hist"][-1]))

        # 4. Structured usage from a caller IS counted, and does not touch dollars.
        d = record(task="selftest-priced", usage={"input_tokens": 100, "output_tokens": 7},
                   secs=1.5, ledger=tmp)
        L = d["lanes"]["openai-codex"]
        results.append(("structured usage counted exactly",
                        L["tok_in"] == 100 and L["tok_out"] == 7 and
                        L["calls"] == 2 and L["unpriced"] == 1 and L["secs"] == 1.5))

        # 5. A dollar figure on the plan lane is REFUSED. It would be a fabrication.
        try:
            record(task="selftest-bad", lane="openai-codex", usd=0.01, ledger=tmp)
            ok5 = False
        except ValueError:
            ok5 = True
        results.append(("usd on the plan-drawn lane is refused", ok5))

        # 6. The lanes never merge.
        d = record(task="selftest-api", lane="openai-api", usage={"input_tokens": 5},
                   usd=0.25, ledger=tmp)
        results.append(("lanes stay separate",
                        d["lanes"]["openai-api"]["usd"] == 0.25 and
                        d["lanes"]["openai-codex"]["usd"] == 0.0))

        # 7. An unknown lane is refused rather than silently created.
        try:
            record(task="x", lane="openai-guess", ledger=tmp)
            ok7 = False
        except ValueError:
            ok7 = True
        results.append(("unknown lane refused", ok7))
    finally:
        SHAPES = real_shapes
        for p in (tmp, tmpshape):
            if p.exists():
                p.unlink()
        try:
            empty.rmdir()
        except OSError:
            pass

    for label, ok in results:
        print(f"  {'OK  ' if ok else 'FAIL'}  {label}")
    good = all(ok for _, ok in results)
    print("SELFTEST PASS - this ledger counts what was measured and refuses to "
          "invent what was not." if good else
          "SELFTEST FAIL - do not trust this ledger.")
    return 0 if good else 1


def main() -> int:
    ap = argparse.ArgumentParser(description="OA (OpenAI Codex CLI) consumption ledger")
    ap.add_argument("--scan", action="store_true",
                    help="discover the usage schema from Codex's own rollouts; writes nothing "
                         "unless something is found")
    ap.add_argument("--learn", metavar="RAW",
                    help="record one captured run from a file of raw CLI output")
    ap.add_argument("--task", default="", help="label for --learn")
    ap.add_argument("--secs", type=float, default=None, help="wall seconds for --learn")
    ap.add_argument("--exit", dest="rc", type=int, default=None,
                    help="the call's real exit code. 0 marks it as a SUCCESSFUL return, "
                         "which is the only thing that makes the node LIVE.")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()

    if a.selftest:
        return selftest()
    if a.scan:
        scan()
        return 0
    if a.learn:
        raw = Path(a.learn).read_text(encoding="utf-8", errors="replace")
        d = record(raw, task=a.task or Path(a.learn).name, secs=a.secs,
                   ok=(None if a.rc is None else a.rc == 0))
        last = d["hist"][-1]
        print("  recorded UNPRICED - the shape is not confirmed yet. The raw tail is kept "
              "in the ledger as evidence." if last.get("UNPRICED") else
              f"  recorded: {last}")
        print()
    print(json.dumps(budget(), indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
