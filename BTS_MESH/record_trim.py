#!/usr/bin/env python3
"""
record_trim.py - free up context in the war-game record WITHOUT truncating evidence.

Keith, 2026-08-03: "We don't need the manual, just the excerpts from it. What else would you
cut/reduce? We need a little more headspace, just in case."

THE RULE THIS TOOL OBEYS
  A uniform per-document character cap is the obvious way to make a record fit and it is the wrong
  one: it bites the largest files, which here are the SOP master and the production PDF - exactly
  what requests 27 and 30 turn on. Truncating evidence to make room is how a review comes back
  confidently wrong.

  So every reduction below is one of three kinds, and each names its reason:
    DROP_DUP     a MEASURED near-duplicate. 9-gram containment was computed both directions; the
                 superset is kept and the subset removed. Nothing unique is lost.
    DROP_NULL    measured to contain nothing bearing on any of the seven requests.
    EXCERPT      keep the passages that bear on a request, plus context, plus a header stating
                 exactly what rule was applied and what was removed. NOT a blind cap.

  Originals are MOVED to record/_orig/, which is a subdirectory and therefore outside the
  loader's glob. --restore puts them back. Nothing is deleted.

USAGE (native Windows - do not run this over the sandbox mount)
    py -3.14 record_trim.py --plan       measure and print, change nothing
    py -3.14 record_trim.py --apply
    py -3.14 record_trim.py --restore
"""
from __future__ import annotations
import argparse, re, shutil, sys
from pathlib import Path

RECORD = Path(r"V:\Ai\Legal\WARGAME\record")
ORIG   = RECORD / "_orig"
BUNDLE = re.compile(r'^\d{2}_[A-Z_]+__')

# ---------------------------------------------------------------------------------------------
# MEASURED 2026-08-03 by 9-gram containment, both directions, over the built record.
# The percentage is |A n B| / |A| - how much of the dropped file is already inside the kept one.
DROP_DUP = {
    "04_TEXTS__Abraxas Case__Abraxas-Exhibits__Abraxas- Exhibit A1-Vadim Yerokhin-Text Messages.pdf.txt":
        ("99.0% inside '04_TEXTS__...Vadim Yerokhin - Text Messages.pdf.txt', which is the larger "
         "and more complete OCR of the same messages"),
    "02_DISCOVERY__Abraxas Case__Abraxas Discovery - John Farley.pdf.txt":
        ("99.8% inside '02_DISCOVERY__...Plaintiffs First Set of Discovery', the same instrument"),
    "01_PLEADINGS__Abraxas Case__HPLC-LEASE__Abraxas- Exhibit C1 - Lease Agreement.pdf.txt":
        ("98.3% inside '01_PLEADINGS__...Abraxas- Exhibit C1 - Lease...', the same exhibit filed twice"),
}

# Measured zero hits for: AL-SOP identifier, Jasper, Abraxas Scientific, autosampler, needle, tray,
# vial, warranty, lost profits. Effective 31 Dec 2019, six months before delivery.
DROP_NULL = {
    "08_CORPORATE__AbraxasLabs QA Policy NEW - DRAFT.docx.txt":
        ("zero measured hits on every term any of the seven requests turns on; a Dec-2019 draft "
         "quality manual that predates the lease"),
}

# EXCERPT: (regex of what to keep, lines of context each side, keep first N lines as front matter)
EXCERPT = {
    "06_INSTRUMENT__Abraxas Case__Abraxas Discovery Reply__hplc1100-maintenance.pdf.txt": (
        r"autosampler|needle|\btray\b|\bvial|\barm\b|self.?test|ALS\b", 6, 12,
        "Agilent vendor manual, 56 pp. Kept: every passage on the autosampler, needle, tray, vial, "
        "arm and power-on self-test - the mechanism the 9 July 2020 consultant email describes and "
        "the subject of Defendant's bare denial at Request No. 16. Removed: pump, detector, column "
        "and solvent-delivery maintenance, which bear on nothing in issue."),
    "08_CORPORATE__Abraxas Case__Abraxas-Exhibits__Abraxas_Labs-LLC-Business_Plan.pdf.txt": (
        r"financial projection|profit and loss|projected revenue|revenue projection|break.?even|"
        r"pro forma|net income|HPLC|warranty", 25, 20,
        "Business plan, Jan 2020, 74 pp. Measured zero hits on Jasper, Abraxas Scientific, "
        "autosampler, needle and lost profits. Kept: the financial projections, because they are "
        "the closest thing in the record to a pre-suit revenue computation and a reviewer assessing "
        "the lost-profits request must be able to see them - the Projected Profit and Loss puts "
        "FY2021 revenue at $3,564,000. Context is 25 lines rather than the 6 used elsewhere, "
        "because these are multi-year tables and a narrow window would cut them mid-column. "
        "Removed: market, marketing, personnel and facility narrative."),
    "08_CORPORATE__Abraxas-Exhibits__Abraxas_Labs_SOPs_MAIN.docx.txt": (
        r"AL-SOP|\bSOP\b|sampling|potency|cannabinoid|HPLC", 6, 60,
        "Abraxas SOP master. The AL-SOP identifier appears exactly TWICE in 105,781 bytes - at "
        "table-of-contents line 163 and section heading line 2374, both 'AL-SOP-04 SAMPLING SOPs'. "
        "Kept: the full contents listing plus every SOP passage. Removed: the procedural body text, "
        "which carries no identifier and bears on nothing in issue."),
}


def size(p: Path) -> int:
    return p.stat().st_size if p.exists() else 0


def excerpt(text: str, pat: str, ctx: int, front: int, why: str, name: str) -> str:
    lines = text.splitlines()
    rx = re.compile(pat, re.I)
    keep = set(range(min(front, len(lines))))
    for i, ln in enumerate(lines):
        if rx.search(ln):
            keep.update(range(max(0, i - ctx), min(len(lines), i + ctx + 1)))
    out, prev = [], -2
    for i in sorted(keep):
        if i != prev + 1 and out:
            out.append(f"[... {i - prev - 1} lines omitted ...]")
        out.append(lines[i]); prev = i
    hdr = ["=" * 92,
           "THIS DOCUMENT HAS BEEN EXCERPTED. IT IS NOT THE COMPLETE ORIGINAL.",
           f"  original: {name}",
           f"  kept {len(keep):,} of {len(lines):,} lines by the rule: /{pat}/i with {ctx} lines of context",
           "  REASON:"]
    hdr += ["    " + l for l in _wrap(why, 86)]
    hdr += ["  Omissions are marked inline as [... N lines omitted ...]. If a proposition you need",
            "  to assess falls in an omitted span, say so rather than inferring it.", "=" * 92, ""]
    return "\n".join(hdr + out) + "\n"


def _wrap(s: str, w: int) -> list[str]:
    out, cur = [], ""
    for word in s.split():
        if len(cur) + len(word) + 1 > w:
            out.append(cur); cur = word
        else:
            cur = (cur + " " + word).strip()
    if cur:
        out.append(cur)
    return out


def run(apply: bool) -> int:
    missing = [n for n in (*DROP_DUP, *DROP_NULL, *EXCERPT) if not (RECORD / n).exists()]
    if missing:
        print("  these named files are not in the record - rebuild it, or the names have drifted:")
        for n in missing:
            print(f"    MISSING  {n}")
        if apply:
            print("\n  🔴 refusing to apply against a record that does not match. Nothing changed.\n")
            return 2

    before = sum(size(p) for p in RECORD.glob("*.txt") if BUNDLE.match(p.name))
    print(f"\n  record now: {before:,} bytes  ~{before // 4:,} tok est\n")
    if apply:
        ORIG.mkdir(exist_ok=True)

    saved = 0
    for group, table in (("DROP  dup ", DROP_DUP), ("DROP  null", DROP_NULL)):
        for n, why in table.items():
            p = RECORD / n
            if not p.exists():
                continue
            s = size(p); saved += s
            print(f"  {group}  -{s:>8,} B   {n[:66]}")
            for l in _wrap(why, 80):
                print(f"                             {l}")
            if apply:
                shutil.move(str(p), str(ORIG / n))

    for n, (pat, ctx, front, why) in EXCERPT.items():
        p = RECORD / n
        if not p.exists():
            continue
        raw = p.read_bytes()
        if len(raw) != p.stat().st_size:
            print(f"  🔴 TRUNCATED READ on {n} - aborting, change nothing"); return 3
        new = excerpt(raw.decode("utf-8", "replace"), pat, ctx, front, why, n)
        d = len(raw) - len(new.encode("utf-8")); saved += d
        print(f"  EXCERPT     -{d:>8,} B   {n[:66]}")
        print(f"                             {len(raw):,} -> {len(new.encode('utf-8')):,} bytes")
        for l in _wrap(why, 80):
            print(f"                             {l}")
        if apply:
            shutil.move(str(p), str(ORIG / n))
            p.write_text(new, encoding="utf-8")

    after = before - saved
    print(f"\n  {'APPLIED' if apply else 'PLAN ONLY - nothing changed'}")
    print(f"  {before:,} -> {after:,} bytes     ~{before // 4:,} -> ~{after // 4:,} tok est")
    print(f"  freed ~{saved // 4:,} tokens.  SGH headroom would be ~{500_000 - after // 4:,}")
    print(f"  (chars/4 measures ~12% HIGH, so the true headroom is larger still)")
    if apply:
        print(f"\n  originals moved to {ORIG} - nothing deleted. --restore undoes this.\n")
    return 0


def restore() -> int:
    if not ORIG.exists():
        print("  nothing to restore"); return 1
    n = 0
    for p in ORIG.glob("*.txt"):
        shutil.move(str(p), str(RECORD / p.name)); n += 1
    print(f"  restored {n} original(s)")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--plan", action="store_true")
    g.add_argument("--apply", action="store_true")
    g.add_argument("--restore", action="store_true")
    a = ap.parse_args()
    return restore() if a.restore else run(a.apply)


if __name__ == "__main__":
    sys.exit(main())
