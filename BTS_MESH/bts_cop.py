#!/usr/bin/env python3
"""bts_cop.py — the CoPG (GitHub Copilot CLI) credit ledger.  2026-07-30

    "Assume the current usage represents 1% and measure it in future to update. Keep track of your
     usage to compare with their metered numbers later (numerator)."   — Keith, 2026-07-30

WHY A LEDGER AT ALL
-------------------
CoPG is the fourth lane and the ONLY scriptable route to `X:\\My Drive\\BTS_SGH_Handoff`. It will get
used. It is metered in **GitHub AI Credits (1 credit = $0.01 USD)** against an allowance GitHub
publishes for paid plans and **NOT for Free** — the docs table covers Pro/Pro+/Max only, and the
account's own Usage panel shows **percentages with no absolute numbers**.

So the denominator has to be DERIVED, and this file exists to make the numerator exact first.
The xAI ledger is the precedent worth copying and the warning worth heeding: 204 GW calls went
unpriced and still distort the month-to-date figure. **Never let a call go unrecorded.**

THE DERIVATION
--------------
    cap_credits  =  credits_spent (exact, here)  /  (pct_used / 100)

One tick of that percentage from 0% to 1% pins the allowance. Until then:

  * **PROVISIONAL_CAP is Keith's 1% assumption**, and it is deliberately CONSERVATIVE — it treats
    today's spend as if it were already 1% of the allowance, which makes the budget look smaller
    than it is. Planning against a low cap is safe; planning against a high one is not.
  * ⚠ **It is almost certainly an UNDER-estimate.** The panel displayed **0%** after 0.73 credits.
    If 0% means "under 0.5%", the true cap is **above ~146 credits**, i.e. at least double the
    provisional figure. Both numbers are recorded so nobody mistakes the assumption for a reading.
  * Nothing here is `[V]`. The cap stays `[U]` until the percentage moves.

CROSS-CHECK, LATER: the Copilot usage-metrics API reports AI credits consumed per user per day
(changelog 2026-06-19), and there is a REST billing-usage endpoint. Reconcile monthly — the same
discipline that caught the $299 phantom credit.

USAGE
    from bts_cop import record, budget
    record(raw_cli_output, task="fs_roots probe")     # parses the CLI's own footer
    python bts_cop.py --selftest                      # negative control
"""
from __future__ import annotations

import json
import os
import re
import sys
import time

_HERE = os.path.dirname(os.path.abspath(__file__))
LEDGER = os.path.join(_HERE, "cop_spend.json")

# Keith's 1% anchor, 2026-07-30: 0.73 credits observed while the panel still read 0%.
ANCHOR_CREDITS = 0.73
ANCHOR_PCT = 1.0                       # ASSUMED, not read
PROVISIONAL_CAP = ANCHOR_CREDITS / (ANCHOR_PCT / 100.0)    # = 73 credits = $0.73  [U]
LOWER_BOUND_CAP = ANCHOR_CREDITS / 0.005                   # = 146 credits, if 0% means "<0.5%"
USD_PER_CREDIT = 0.01

# The CLI prints its own footer. Captured verbatim 2026-07-30 20:42:
#   AI Credits 0.73 (21s)
#   Tokens     ↑ 47.4k (23.7k cached) • ↓ 382 (192 reasoning)
_CREDITS = re.compile(r"AI\s+Credits\s+([0-9]+(?:\.[0-9]+)?)", re.I)
_SECS = re.compile(r"AI\s+Credits\s+[0-9.]+\s*\((\d+)s\)", re.I)
_TOKENS = re.compile(r"Tokens.*?([0-9.]+)k?\s*\(([0-9.]+)k?\s*cached\).*?([0-9]+)", re.I | re.S)


def _num(s: str, k: bool) -> float:
    v = float(s)
    return v * 1000 if k else v


def parse(raw: str) -> dict:
    """Pull the metering footer out of a CoPG run. Returns {} if the footer is absent —
    an ABSENT footer must never be recorded as a zero-cost call."""
    m = _CREDITS.search(raw or "")
    if not m:
        return {}
    out = {"credits": float(m.group(1))}
    s = _SECS.search(raw)
    if s:
        out["secs"] = int(s.group(1))
    t = _TOKENS.search(raw)
    if t:
        out["tok_in"] = _num(t.group(1), "k" in raw[t.start():t.end()].split("cached")[0].lower())
        out["tok_cached"] = _num(t.group(2), True)
        out["tok_out"] = float(t.group(3))
    return out


def _load() -> dict:
    try:
        with open(LEDGER, encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return {}


def record(raw: str, task: str = "", ledger: str = None) -> dict:
    """Append one call to the ledger. An unparseable run is recorded as UNPRICED, loudly —
    it is NOT dropped and NOT counted as zero. (204 unpriced GW calls are why.)"""
    path = ledger or LEDGER
    d = _load() if path == LEDGER else {}
    month = time.strftime("%Y-%m")
    if d.get("month") != month:
        d = {"month": month, "credits": 0.0, "calls": 0, "unpriced": 0, "hist": []}
    p = parse(raw)
    d["calls"] = d.get("calls", 0) + 1
    if p:
        d["credits"] = round(d.get("credits", 0.0) + p["credits"], 4)
        d["hist"] = (d.get("hist") or [])[-499:] + [{"t": int(time.time()), "task": task, **p}]
    else:
        d["unpriced"] = d.get("unpriced", 0) + 1
        d["hist"] = (d.get("hist") or [])[-499:] + [{"t": int(time.time()), "task": task,
                                                     "UNPRICED": True}]
    with open(path, "w", encoding="utf-8", newline="") as fh:
        json.dump(d, fh, indent=2)
    return d


def budget() -> dict:
    d = _load()
    used = float(d.get("credits") or 0.0)
    return {
        "month": d.get("month"), "calls": d.get("calls", 0),
        "unpriced_calls": d.get("unpriced", 0),
        "credits_used": round(used, 4), "usd_used": round(used * USD_PER_CREDIT, 4),
        "cap_provisional_[U]": PROVISIONAL_CAP,
        "cap_lower_bound_[U]": LOWER_BOUND_CAP,
        "pct_of_provisional": round(100 * used / PROVISIONAL_CAP, 1) if PROVISIONAL_CAP else None,
        "basis": "Keith's 1% anchor 2026-07-30 (0.73 credits at a displayed 0%). ASSUMED, not read. "
                 "Derive the true cap the first time the settings page shows a non-zero percent: "
                 "cap = credits_used / (pct/100).",
    }


def selftest() -> int:
    """NEGATIVE CONTROL. Uses the CLI footer captured verbatim on 2026-07-30, plus a run with NO
    footer, which must be recorded as UNPRICED rather than silently as free."""
    real = ("Changes    +0 -0\n"
            "AI Credits 0.73 (21s)\n"
            "Tokens     \u2191 47.4k (23.7k cached) \u2022 \u2193 382 (192 reasoning)\n")
    p = parse(real)
    ok1 = abs(p.get("credits", 0) - 0.73) < 1e-9 and p.get("secs") == 21
    ok2 = parse("no footer here at all") == {}
    # Write the throwaway ledger to the OS temp dir, never into the tree: the sandbox mount
    # permits creation but REFUSES deletion, so a selftest artefact written here cannot clean up
    # after itself and leaves litter in BTS_MESH. Measured 2026-07-30.
    import tempfile
    tmp = os.path.join(tempfile.gettempdir(), "_cop_selftest.json")
    try:
        d1 = record(real, task="selftest-priced", ledger=tmp)
        d2 = record("no footer", task="selftest-unpriced", ledger=tmp)
        ok3 = d2["unpriced"] >= 1 and d2["calls"] == 1  # fresh temp ledger each call by design
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)
    print(f"  parse real footer      -> {p}   {'OK' if ok1 else 'FAIL'}")
    print(f"  parse missing footer   -> {{}}   {'OK' if ok2 else 'FAIL'}")
    print(f"  unpriced run recorded  -> {'OK' if ok3 else 'FAIL'} (must NOT be counted as $0)")
    print(f"  budget                 -> {json.dumps(budget(), indent=2)}")
    good = ok1 and ok2 and ok3
    print("SELFTEST PASS — a metered run is priced, an unmetered run is flagged, never dropped."
          if good else "SELFTEST FAIL — this ledger cannot be trusted.")
    return 0 if good else 1


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(selftest())
    print(json.dumps(budget(), indent=2))
