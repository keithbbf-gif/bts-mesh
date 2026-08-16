#!/usr/bin/env python3
"""
Run on the HOST (Windows). Two jobs:

1. VERIFY that bts_sgh.py still compiles and that the search governor is live. The Linux sandbox
   reported a false SyntaxError on this file (a known mount-corruption artefact), so the only
   trustworthy check is compiling it here, where the file actually lives.

2. RECONCILE the spend ledger. On 2026-07-12/13 two GROUNDED calls were made by bypassing
   bts_sgh.ask() and hitting the API directly, so sgh_spend.json never charged them:
       $1.315596  lit-markers   (grok-4.5 + web_search, 780,379 tokens)   2026-07-12 20:00
       $1.613868  lit-spectra   (grok-4.5 + web_search)                   2026-07-13 00:58
   The xAI console corroborates the first exactly ($1.32 on Jul 12). Both are written into the
   ledger here so the dashboard stops under-reporting the month.
"""
import json, os, py_compile, time

HERE = os.path.dirname(os.path.abspath(__file__))
SGH = os.path.join(HERE, "bts_sgh.py")
LEDGER = os.path.join(HERE, "sgh_spend.json")

MISSING = [
    {"t": 1783908010, "usd": 1.315596, "tok": 780379,
     "note": "lit-markers, grounded, direct-API (bypassed ask())"},
    {"t": 1783922280, "usd": 1.613868, "tok": None,
     "note": "lit-spectra, grounded, direct-API (bypassed ask())"},
]

print("=" * 70)
print("1. COMPILE CHECK (host-side = ground truth)")
try:
    py_compile.compile(SGH, doraise=True)
    print("   bts_sgh.py compiles cleanly.")
except py_compile.PyCompileError as e:
    print("   REAL SYNTAX ERROR:\n", e)
    raise SystemExit(2)

import importlib.util
spec = importlib.util.spec_from_file_location("bts_sgh", SGH)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
print("   SEARCH_ON_PAID_RAIL  =", m.SEARCH_ON_PAID_RAIL, "(must be False)")
print("   PER_CALL_CEILING_USD =", m.PER_CALL_CEILING_USD)
print("   MAX_CALL_USD         =", m.MAX_CALL_USD, "(grounded worst case, corrected from 0.50)")

print("\n2. NEGATIVE CONTROL — a grounded call with no authorisation must be REFUSED")
r = m.ask("this must never reach the API", search=True)
ok = (r.get("ok") is False and r.get("reason") == "SEARCH_REFUSED_ON_PAID_RAIL")
print("   refused? ", ok, "->", r.get("reason"))
print("   free lanes offered:", r.get("free_lanes"))
if not ok:
    print("   !! GOVERNOR IS NOT WORKING — a search call would have been billed.")
    raise SystemExit(3)

r2 = m.ask("authorised search", search=True, spend_ok=0.01)
print("   spend_ok too low is refused? ", r2.get("reason") == "SPEND_OK_TOO_LOW", "->", r2.get("reason"))

print("\n3. LEDGER RECONCILE")
d = json.load(open(LEDGER, encoding="utf-8"))
have = {round(h["usd"], 6) for h in d.get("hist", [])}
added = 0.0
for c in MISSING:
    if round(c["usd"], 6) in have:
        print("   already present, skipping: $%.6f" % c["usd"]); continue
    d.setdefault("hist", []).append({"t": c["t"], "usd": c["usd"], "tok": c["tok"], "note": c["note"]})
    d["WORK"] = round(d.get("WORK", 0.0) + c["usd"], 6)
    d["calls"] = d.get("calls", 0) + 1
    d["tool_calls"] = d.get("tool_calls", 0) + 2   # grounded: at least 2 searches each (measured)
    added += c["usd"]
    print("   charged $%.6f  (%s)" % (c["usd"], c["note"]))

json.dump(d, open(LEDGER, "w", encoding="utf-8"), indent=1)
b = m.budget()
print("\n   ledger now: WORK $%.4f | POLL $%.4f | spent $%.4f of $%.2f (%.1f%%) | left $%.4f"
      % (d["WORK"], d.get("POLL", 0.0), b["spent"], b["budget"], b["pct"], b["left"]))
print("   added this run: $%.4f" % added)
print("\nDONE.")
