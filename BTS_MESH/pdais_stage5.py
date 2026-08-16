#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""pdais_stage5.py - PDAiS STAGE 5: order documents by THE DATE THE DOCUMENT IS. 2026-08-12.

PLM-35. An agent survey of the open-source landscape found the components healthy
(`dateparser`, `datefinder`) and **the SELECTOR missing everywhere**. The only project
running the full loop is `paperless-ngx`, and its rule is literally *"first date that
parses wins"* - which mis-dates any letter opening

    "Further to your letter of 3 March 2019, we write to confirm..."

as 2019-03-03, when that is the date of a DIFFERENT document being referenced. A corpus
ordered that way puts replies before the things they reply to, and a chronology that is
wrong in that specific way is worse than no chronology: it invents a sequence of events.

THE INSIGHT THE OTHER TOOLS MISS
--------------------------------
Extraction is solved. **ROLE ASSIGNMENT is not.** A date in a document is not a fact about
the document until you know WHAT THAT DATE IS DOING there:

    DATELINE      "12 August 2026" alone near the top, or after a place name  -> STRONG
    EXECUTION     "Dated this 12th day of August, 2026"                       -> STRONG
    SIGNATURE     a date within a few lines of a signature block              -> MEDIUM
    RECEIVED      "Received: 12 Aug 2026", a stamp, a filing endorsement      -> MEDIUM
    REFERENCE     "your letter of...", "the agreement dated...", "see our..." -> 🔴 NEVER
    BODY          anything else                                              -> WEAK

⇒ **A REFERENCE DATE IS EVIDENCE ABOUT ANOTHER DOCUMENT.** Treating it as this document's
  date is the whole bug, and it is the single most common one.

REFUSES RATHER THAN GUESSES
---------------------------
Returns `INDETERMINATE` when the best candidates tie, when the only dates found are
references, or when nothing parses. **INDETERMINATE is not failure** - PDAiS says so
explicitly, and the size of the indeterminate set is the first thing a pilot must measure.
A tool that always returns a date makes the error invisible.

USAGE
    from pdais_stage5 import document_date, order_documents
    py -3.14 pdais_stage5.py --selftest
"""
from __future__ import annotations

import re
import sys

MONTHS = ("january february march april may june july august september october "
          "november december").split()
ABBR = [m[:3] for m in MONTHS]

_D = r"(?:\d{1,2})"
_Y = r"(?:19|20)\d{2}"
_MON = r"(?:%s)" % "|".join(MONTHS + ABBR)

PATTERNS = [
    re.compile(r"\b(%s)\s+(%s)\s*,?\s*(%s)\b" % (_MON, _D, _Y), re.I),      # August 12, 2026
    re.compile(r"\b(%s)(?:st|nd|rd|th)?\s+(?:day\s+of\s+)?(%s)\s*,?\s*(%s)\b"
               % (_D, _MON, _Y), re.I),                                      # 12th day of August 2026
    re.compile(r"\b(\d{1,2})[/-](\d{1,2})[/-](%s)\b" % _Y),                  # 8/12/2026
    re.compile(r"\b(%s)-(\d{2})-(\d{2})\b" % _Y),                            # 2026-08-12
]

REFERENCE_CUES = (
    "your letter of", "our letter of", "letter dated", "agreement dated",
    "dated on or about", "referenced", "further to", "in reply to", "in response to",
    "see our", "your ref", "our ref", "as set out in", "the invoice dated",
    "the notice dated", "pursuant to the", "referred to in", "attached hereto",
)
EXECUTION_CUES = ("dated this", "executed this", "signed this", "in witness whereof",
                  "day of")
RECEIVED_CUES = ("received", "filed", "date stamp", "entered", "docketed", "posted")
SIGNATURE_CUES = ("sincerely", "yours truly", "respectfully", "regards", "signature",
                  "/s/", "very truly yours")

ROLE_WEIGHT = {"DATELINE": 100, "EXECUTION": 95, "RECEIVED": 60, "SIGNATURE": 55,
               "BODY": 20, "REFERENCE": 0}


def _norm(m, pat_index):
    g = [x for x in m.groups() if x]
    try:
        if pat_index in (0, 1):
            if pat_index == 0:
                mon, day, yr = g[0], g[1], g[2]
            else:
                day, mon, yr = g[0], g[1], g[2]
            mon = mon.lower()[:3]
            month = ABBR.index(mon) + 1
            return (int(yr), month, int(day))
        if pat_index == 2:
            a, b, yr = int(g[0]), int(g[1]), int(g[2])
            return (yr, a, b)                       # US order; this corpus is Oklahoma
        return (int(g[0]), int(g[1]), int(g[2]))
    except (ValueError, IndexError):
        return None


def _role(text: str, start: int, end: int, line_no: int, total_lines: int) -> str:
    lo = max(0, start - 90)
    before = text[lo:start].lower()
    after = text[end:end + 60].lower()
    window = before + " " + after
    if any(c in before for c in REFERENCE_CUES):
        return "REFERENCE"
    if any(c in window for c in EXECUTION_CUES):
        return "EXECUTION"
    if any(c in window for c in RECEIVED_CUES):
        return "RECEIVED"
    if any(c in window for c in SIGNATURE_CUES):
        return "SIGNATURE"
    if line_no <= max(6, total_lines * 0.08):
        stripped = text[lo:end].strip().splitlines()
        if stripped and len(stripped[-1]) < 60:
            return "DATELINE"
    return "BODY"


def candidates(text: str):
    """Every date found, with its ROLE. Reading only."""
    out = []
    starts = [0]
    for i, ch in enumerate(text):
        if ch == "\n":
            starts.append(i + 1)
    total = len(starts)

    def line_of(pos):
        lo, hi = 0, total - 1
        while lo < hi:
            mid = (lo + hi + 1) // 2
            if starts[mid] <= pos:
                lo = mid
            else:
                hi = mid - 1
        return lo + 1

    for idx, pat in enumerate(PATTERNS):
        for m in pat.finditer(text):
            d = _norm(m, idx)
            if not d or not (1 <= d[1] <= 12) or not (1 <= d[2] <= 31):
                continue
            ln = line_of(m.start())
            out.append({"date": d, "text": m.group(0), "line": ln,
                        "role": _role(text, m.start(), m.end(), ln, total)})
    return out


def document_date(text: str):
    """Return (date_tuple_or_None, verdict, evidence).

    verdict is one of: the role that won, or INDETERMINATE with a reason."""
    cands = candidates(text)
    if not cands:
        return None, "INDETERMINATE: no parseable date", []
    usable = [c for c in cands if c["role"] != "REFERENCE"]
    if not usable:
        return None, ("INDETERMINATE: every date found is a REFERENCE to another "
                      "document"), cands
    best = max(ROLE_WEIGHT[c["role"]] for c in usable)
    top = [c for c in usable if ROLE_WEIGHT[c["role"]] == best]
    distinct = {c["date"] for c in top}
    if len(distinct) > 1:
        return None, ("INDETERMINATE: %d equally-weighted %s dates disagree"
                      % (len(distinct), top[0]["role"])), top
    return top[0]["date"], top[0]["role"], top


def order_documents(docs: dict):
    """{name: text} -> (ordered [(date,name,verdict)], indeterminate [(name,reason)])."""
    dated, unknown = [], []
    for name, text in docs.items():
        d, verdict, _ = document_date(text)
        (dated.append((d, name, verdict)) if d else unknown.append((name, verdict)))
    dated.sort(key=lambda x: x[0])
    return dated, unknown


def selftest() -> int:
    checks = []
    ref = ("Smith & Co\n123 Main St\n\nAugust 12, 2026\n\nDear Sir,\n\n"
           "Further to your letter of 3 March 2019, we write to confirm the position.\n\n"
           "Sincerely,\n")
    d, v, _ = document_date(ref)
    checks.append(("the DATELINE wins over a referenced date", d == (2026, 8, 12)))
    checks.append(("and the reference is not what was chosen", d != (2019, 3, 3)))

    only_ref = "We refer to your letter of 3 March 2019 and say nothing else.\n"
    d2, v2, _ = document_date(only_ref)
    checks.append(("a document with ONLY a reference date is INDETERMINATE",
                   d2 is None and "REFERENCE" in v2))

    exe = ("THIS AGREEMENT\n\nsundry recitals here in the body of the document\n\n"
           "Dated this 5th day of January, 2020.\n")
    d3, v3, _ = document_date(exe)
    checks.append(("an execution clause is found", d3 == (2020, 1, 5)))

    tie = ("memo\n\nbody text\n\nDated this 5th day of January, 2020.\n"
           "Dated this 6th day of January, 2020.\n")
    d4, v4, _ = document_date(tie)
    checks.append(("two equally-weighted dates that disagree -> INDETERMINATE",
                   d4 is None and "disagree" in v4))

    d5, v5, _ = document_date("no dates at all in this document")
    checks.append(("no date -> INDETERMINATE, not a guess",
                   d5 is None and "no parseable" in v5))

    docs = {"reply": ref, "old": exe, "mystery": only_ref}
    ordered, unknown = order_documents(docs)
    checks.append(("ordering puts 2020 before 2026",
                   [n for _, n, _ in ordered] == ["old", "reply"]))
    checks.append(("and the indeterminate one is REPORTED, not dropped silently",
                   [n for n, _ in unknown] == ["mystery"]))

    print("=" * 78)
    print("  pdais_stage5 --selftest")
    print("=" * 78)
    for label, good in checks:
        print("  %s  %s" % ("OK  " if good else "FAIL", label))
    bad = [l for l, g in checks if not g]
    print("SELFTEST PASS - a referenced date never becomes the document's date, and a tie "
          "refuses." if not bad else "SELFTEST FAIL - %d check(s)." % len(bad))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(selftest() if "--selftest" in sys.argv else selftest())
