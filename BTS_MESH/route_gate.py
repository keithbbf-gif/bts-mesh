#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""route_gate.py - PARSE -> CLASSIFY -> ROUTE. PLM-33. Keith-ordered 2026-08-02.

    "We need a more formalized prompt action system to govern your action - parse /
     delegate / answer / execute - and if the path is delegate, PDAiS."

WHY A GATE AND NOT A GUIDELINE
------------------------------
On 2026-08-02 that routing decision was improvised roughly fifty times and got it wrong at
least four: soloing work a prepaid rail should have done; delegating to Claude subagents
when Keith meant SGH/GEM/CoPG; converting mesh documents to .docx for a man with no use
for them; and concluding "not in the record" from a search of ONE FOLDER.

**C-01 is at count 5 with no mechanism.** Praise, correction and agreement do not persist -
only disk does - so the fix cannot be "remember to delegate." It has to be a step that
runs and can REFUSE.

THE FOUR ROUTES
    ANSWER   - knowledge, already in context, or one grep away. No spend.
    EXECUTE  - a deterministic operation on this machine. Cowork does it.
    DELEGATE - reading, research, judgement, or bulk. A PREPAID RAIL DOES IT.
    ASK      - money, credentials, elevation, or a decision that is Keith's.

TWO REFUSALS THAT MAKE IT REAL
    1. 🔴 A DELEGATE ROUTE WITHOUT A PDAiS-PREPARED FEED IS REFUSED. Handing a node a raw
       folder is how four families got paid to read Keith's W-9s.
    2. 🔴 A NEGATIVE FINDING WITHOUT A SCOPE DECLARATION IS REFUSED. "Not in the record"
       is not a finding; "I searched X, I did not search Y" is. That distinction is
       S-117/C-12 and it has cost real money twice.

USAGE
    from route_gate import route
    r = route("summarise every PDF in the corpus")   # -> DELEGATE, with the reason
    py -3.14 route_gate.py --selftest
"""
from __future__ import annotations

import re
import sys

ASK_CUES = ("buy", "purchase", "pay", "billing", "credit card", "invoice", "subscribe",
            "sign in", "log in", "password", "mfa", "2fa", "oauth", "consent",
            "elevate", "administrator", "uac", "authorize a charge", "spend money")

DELEGATE_CUES = ("research", "survey", "read every", "read all", "summarise every",
                 "summarize every", "review the", "cross-check", "find out whether",
                 "what does the literature", "search the web", "compare sources",
                 "analyse the corpus", "analyze the corpus", "go through the",
                 "look through", "case law", "second opinion", "critique", "adversarial")

EXECUTE_CUES = ("run ", "rebuild", "publish", "copy ", "move ", "rename", "delete",
                "stage ", "install", "register", "regenerate", "measure", "benchmark",
                "queue ", "schedule")

BULK = re.compile(r"\b(all|every|each)\b.{0,24}\b(file|files|document|documents|pdf|pdfs|"
                  r"page|pages|record|records|email|emails)\b", re.I)

NEGATIVE_CLAIM = re.compile(r"\b(not in the record|nothing found|no such|does not exist|"
                            r"there is no|none found|no evidence of)\b", re.I)

SCOPE_DECL = re.compile(r"\bI (searched|checked|read|globbed|grepped)\b", re.I)


def classify(task: str) -> tuple:
    t = (task or "").lower()
    if any(c in t for c in ASK_CUES):
        return ("ASK", "touches money, credentials or elevation — Keith's, always")
    if BULK.search(t) or any(c in t for c in DELEGATE_CUES):
        return ("DELEGATE", "reading/judgement/bulk — a prepaid rail should do this, "
                            "not Cowork's own allotment (C-01, count 5)")
    if any(c in t for c in EXECUTE_CUES):
        return ("EXECUTE", "a deterministic operation on this machine")
    return ("ANSWER", "answerable from knowledge or one grep — no spend")


def route(task: str, feed_prepared: bool = False, scope: str = "",
          claim: str = "") -> dict:
    """Return the routing decision, INCLUDING refusals. Never silently downgrades."""
    kind, why = classify(task)
    out = {"task": task, "route": kind, "why": why, "refusals": [], "ok": True}

    if kind == "DELEGATE" and not feed_prepared:
        out["refusals"].append(
            "REFUSED: the delegate path requires a PDAiS-prepared feed. Handing a node a "
            "raw folder is how four model families were paid to read tax returns and a "
            "1,309-page unrelated application (PLM-34). Prepare the feed, then re-route.")
        out["ok"] = False

    if claim and NEGATIVE_CLAIM.search(claim) and not SCOPE_DECL.search(scope or ""):
        out["refusals"].append(
            "REFUSED: a NEGATIVE finding without a scope declaration. 'Not in the record' "
            "is a claim about the whole record; what you have is a claim about what you "
            "searched. State 'I searched X; I did not search Y' (S-117 / C-12).")
        out["ok"] = False

    if kind == "DELEGATE":
        out["rails"] = ["SGH (grok-4.5)", "GEM (gemini)", "GW (grok-build)",
                        "CoPG (Copilot CLI)"]
        out["note"] = ("Claude subagents are the SAME FAMILY with the SAME PRIORS and "
                       "spend KEITH'S OWN ALLOTMENT — the one budget that runs out. "
                       "Idle prepaid capacity is wasted money, not savings.")
    return out


def selftest() -> int:
    checks = []
    r = route("read every PDF in the corpus and summarise them")
    checks.append(("bulk reading routes to DELEGATE", r["route"] == "DELEGATE"))
    checks.append(("and it REFUSES without a prepared feed",
                   not r["ok"] and any("PDAiS" in x for x in r["refusals"])))
    r2 = route("read every PDF in the corpus and summarise them", feed_prepared=True)
    checks.append(("with a prepared feed it proceeds", r2["ok"]))
    checks.append(("and it names the prepaid rails, not Claude subagents",
                   "SGH (grok-4.5)" in r2["rails"]))

    r3 = route("buy the OpenAI API credits")
    checks.append(("money routes to ASK", r3["route"] == "ASK"))
    r4 = route("run the R2 publish")
    checks.append(("a deterministic op routes to EXECUTE", r4["route"] == "EXECUTE"))
    r5 = route("what is the capital of France")
    checks.append(("knowledge routes to ANSWER", r5["route"] == "ANSWER"))

    r6 = route("run the search", claim="It is not in the record.")
    checks.append(("a negative claim with NO scope is REFUSED",
                   not r6["ok"] and any("scope" in x for x in r6["refusals"])))
    r7 = route("run the search", claim="It is not in the record.",
               scope="I searched V:\\Ai\\Legal\\CORPUS; I did not search the OCR backlog.")
    checks.append(("the same claim WITH a scope declaration passes", r7["ok"]))

    print("=" * 78)
    print("  route_gate --selftest")
    print("=" * 78)
    for label, good in checks:
        print("  %s  %s" % ("OK  " if good else "FAIL", label))
    bad = [l for l, g in checks if not g]
    print("SELFTEST PASS - it refuses an unprepared delegation and an unscoped negative."
          if not bad else "SELFTEST FAIL - %d check(s)." % len(bad))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(selftest() if "--selftest" in sys.argv else selftest())
