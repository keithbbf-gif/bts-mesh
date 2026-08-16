#!/usr/bin/env python3
"""scars.py — the SCAR RECORD as a QUERY, not a 90 KB read.  2026-07-31

    Keith: "I don't read Rules.md or Scars.md, do you? … see my point?"

He is right, and it collapsed the design. `SCARS.md` was filed as "human-consumed narrative" by both
Cowork and GEM — reasoning from a reader **who does not exist**. Nobody reads it front to back.
Cowork greps it; Keith doesn't open it. Its value was never the prose, it is the QUESTION:

    Has this failure class happened before?

A 90 KB narrative cannot answer that without a full read, which is why the SAME class was hit three
times on 2026-07-30 — measuring one thing and concluding about another — with all three precedents
already written down and unfindable.

WHAT CHANGED, AND WHAT DID NOT
------------------------------
The prose is NOT destroyed and NOT decomposed into keys. Each scar becomes one JSONL record with a
machine-readable envelope and the **body preserved verbatim** — the same shape CLASR uses for
citations (CLAIM / QUOTE / LOC / VERDICT: metadata around an untouched quote).

    {"id","date","title","class":[...],"chars","body"}

JSONL and not TOML **because append-only is the defining property**: one record per line, appending
is a single atomic write, and nothing has to parse or rewrite the file to add an entry. A TOML
array-of-tables would force a whole-file rewrite on every append — the one operation this record
performs most.

⚠ `SCARS.md` REMAINS THE SOURCE OF TRUTH while both exist. This file is a derived INDEX, not a
replacement, and `--rebuild` regenerates it. **Do not hand-edit `scars.jsonl`.**
⚠ The rebuild ALWAYS counts cited-vs-listed and refuses to write on a mismatch. That check caught a
real defect on its first run: 91 parsed vs 95 headings, because four scars carry a DATE RANGE
(`2026-07-15/16`) the regex did not accept. A silent 4-entry loss, caught in one line — which is
precisely the control that would have caught the 26 missing Chapter 4 references.

USAGE
    python scars.py                     # summary: counts by class, by month
    python scars.py mount               # every scar whose class or text matches
    python scars.py --class measurement # class filter only
    python scars.py --id S-90           # one scar, full body
    python scars.py --rebuild           # re-derive scars.jsonl from SCARS.md (counts, then writes)
"""
from __future__ import annotations

import json
import os
import re
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
MD = os.path.join(HERE, "SCARS.md")
JL = os.path.join(HERE, "scars.jsonl")

# A scar heading: '## S-07 · 2026-07-12 · Title'  — the date may be a RANGE '2026-07-15/16'.
HEAD = re.compile(r"^##\s+S-(\d+)\s*·\s*(\d{4}-\d{2}-\d{2}(?:/\d{1,2})?)\s*·\s*(.+?)\s*$", re.M)

CLASSES = [
    ("mount",       r"mount|FUSE|truncat|corrupt"),
    ("naming",      r"\bname|rename|pointer rot|stale pointer"),
    ("encoding",    r"CRLF|utf-8|cp1252|cp437|mojibake|newline"),
    ("measurement", r"cumulative|summed|over-count|wrong key|wrong field|misread|false"),
    ("auth",        r"auth|token|OAuth|credential|login|scope"),
    ("fabrication", r"fabricat|invent|hallucin|quotation|citation"),
    ("control",     r"negative control|never shown to fail|discriminat"),
    ("scheduler",   r"scheduled task|schtasks|watchdog|cadence"),
    ("silent",      r"silently|no error|looked fine|reported success|exit=0"),
]


def rebuild() -> int:
    src = open(MD, encoding="utf-8", errors="replace").read()
    hits = list(HEAD.finditer(src))
    listed = len(re.findall(r"^## S-", src, re.M))
    if len(hits) != listed:
        print(f"  *** REFUSING TO WRITE: cited {len(hits)} != listed {listed}. "
              f"A heading did not parse — fix the regex, do not lose a scar. ***")
        return 1
    recs = []
    for i, m in enumerate(hits):
        body = src[m.end(): hits[i + 1].start() if i + 1 < len(hits) else len(src)].strip()
        blob = m.group(3) + " " + body
        recs.append({"id": "S-%02d" % int(m.group(1)), "date": m.group(2), "title": m.group(3),
                     "class": [k for k, rx in CLASSES if re.search(rx, blob, re.I)],
                     "chars": len(body), "body": body})
    with open(JL, "w", encoding="utf-8", newline="\n") as fh:
        for r in recs:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"  rebuilt {len(recs)} records · cited == listed == {listed} · OK")
    return 0


def drift() -> int:
    """SCARS.md headings vs scars.jsonl records. Returns 0 when they agree.

    🔴 ADDED AT TidyUP2 2026-07-31, AFTER COWORK HAND-EDITED THE DERIVED FILE.
    The docstring at the top of this file already said "Do not hand-edit scars.jsonl", and Cowork
    appended S-97 straight to the JSONL anyway. `--rebuild` regenerates from SCARS.md, so the next
    rebuild would have ERASED it — silently, with the rebuild's own cited==listed check passing,
    because that check compares the Markdown to itself and never looks at the JSONL it overwrites.
    The edit was caught only by luck: the record ALSO had a wrong key name, which threw a KeyError.
    A correctly-shaped hand-edit would have survived until the rebuild ate it.
    ⇒ A WARNING IN A DOCSTRING IS NOT A CONTROL. This is the control.
    """
    if not (os.path.exists(MD) and os.path.exists(JL)):
        return 0
    md = sum(1 for l in open(MD, encoding="utf-8", errors="replace") if l.startswith("## S-"))
    jl = sum(1 for l in open(JL, encoding="utf-8") if l.strip())
    if md != jl:
        print(f"\n  🔴 DRIFT — SCARS.md has {md} scars, scars.jsonl has {jl}.")
        print( "     SCARS.md IS THE SOURCE. scars.jsonl IS DERIVED. Never edit the JSONL.")
        print(f"     {'The JSONL has records the Markdown does not — a hand-edit. It will be ERASED by --rebuild.' if jl > md else 'The JSONL is behind the Markdown.'}")
        print( "     Fix: append to SCARS.md, then  python scars.py --rebuild\n")
        return 1
    return 0


def load() -> list:
    if not os.path.exists(JL):
        print("  scars.jsonl missing — run: python scars.py --rebuild")
        sys.exit(2)
    if drift():
        sys.exit(3)          # refuse to answer questions from a record known to be inconsistent
    return [json.loads(l) for l in open(JL, encoding="utf-8") if l.strip()]


def main() -> int:
    a = sys.argv[1:]
    if "--rebuild" in a:
        return rebuild()
    recs = load()

    if "--id" in a:
        want = a[a.index("--id") + 1].upper()
        for r in recs:
            if r["id"].upper() == want or r["id"].upper() == "S-%02d" % int(want.lstrip("S-") or 0):
                print(f"\n{r['id']} · {r['date']} · {r['title']}\nclass: {', '.join(r['class']) or '(none)'}\n")
                print(r["body"])
                return 0
        print(f"  no scar {want}")
        return 1

    if "--class" in a:
        k = a[a.index("--class") + 1]
        hits = [r for r in recs if k in r["class"]]
    elif a and not a[0].startswith("-"):
        q = a[0].lower()
        hits = [r for r in recs if q in r["title"].lower() or q in r["body"].lower()
                or q in " ".join(r["class"])]
    else:
        print(f"\n  {len(recs)} scars · {recs[0]['date']} -> {recs[-1]['date']}\n")
        print("  BY CLASS (a scar can carry several):")
        for k, n in Counter(c for r in recs for c in r["class"]).most_common():
            print(f"    {k:<14} {n:>3}")
        un = [r["id"] for r in recs if not r["class"]]
        print(f"\n  unclassified: {len(un)}  (add a pattern to CLASSES rather than editing records)")
        print("\n  BY MONTH:")
        for k, n in sorted(Counter(r["date"][:7] for r in recs).items()):
            print(f"    {k}  {n:>3}")
        print("\n  ask a question:  python scars.py mount   |   --class measurement   |   --id S-90")
        return 0

    print(f"\n  {len(hits)} match:\n")
    for r in hits:
        print(f"  {r['id']}  {r['date']}  [{','.join(r['class'])}]\n      {r['title'][:110]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
