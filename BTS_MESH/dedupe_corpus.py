#!/usr/bin/env python3
r"""
dedupe_corpus.py — build a de-duplicated `_ALL_TEXT.md` for the legal corpus.

WHY, 2026-08-01
    `CORPUS\` accumulated from several ingests plus today's OCR run. Measured:
        281 .txt files, 248 distinct contents
        28 exact-duplicate groups covering 61 files, 1,444,397 redundant chars
    And Exhibit B1 (Yerokhin emails) is in the corpus ~2.5 times over:
        master 11,476 word tokens ; parts P1+P2+P3 = 11,486 ; P1 alone x5 copies

    That matters because `_ALL_TEXT.md` is what gets fed to a node. Duplicated
    documents get duplicated WEIGHT — every occurrence count, every "how often
    does he say X", every frequency-based judgement is skewed by whichever
    document happened to be filed twice.

🔴 NON-DESTRUCTIVE BY DESIGN
    It DELETES NOTHING. Every .txt stays on disk — they are derivatives of
    evidence and cost nothing to keep. This rebuilds only the CONCATENATION,
    selecting one representative per content group. If a selection is ever
    wrong, re-run with different flags; no source is at risk.

METHOD
    1. EXACT: normalise (strip the OCR header, page rules, whitespace, case),
       sha256, group. Identical content -> keep one.
    2. NEAR: word-frequency cosine within a group of candidates. Robust to OCR
       noise, unlike shingling — measured today, 8-word shingles gave 20-25%
       containment for text that is provably the same document, because a
       single OCR error breaks every shingle spanning it.
    3. CONTAINMENT: a document whose token count and vocabulary are covered by
       a larger one (master vs parts) is dropped in favour of the master.

    ⚠ A high cosine is NOT proof of duplication on its own. Two filings by the
    same lawyer about the same instrument score high. The tool therefore
    requires cosine >= --near AND a token-count relationship consistent with
    containment before it will treat anything as redundant, and it PRINTS every
    such decision for review rather than burying it.
"""

import argparse
import collections
import hashlib
import math
import os
import re
import sys
from datetime import datetime

C = "/sessions/bold-intelligent-mayer/mnt/Ai/Legal/CORPUS"
HDR = re.compile(r"^#[^\n]*\n(?:#[^\n]*\n)*\n?")
PAGE = re.compile(r"-{4,}\s*page\s+\d+\s*-{4,}", re.I)
WORD = re.compile(r"[a-z0-9@\.]{3,}")


def read_norm(path):
    t = open(path, encoding="utf-8", errors="replace").read()
    t = HDR.sub("", t)
    t = PAGE.sub("", t)
    return re.sub(r"\s+", " ", t).strip()


def bag(text):
    return collections.Counter(WORD.findall(text.lower()))


def cos(a, b):
    na = math.sqrt(sum(v * v for v in a.values()))
    nb = math.sqrt(sum(v * v for v in b.values()))
    ks = set(a) & set(b)
    return sum(a[k] * b[k] for k in ks) / max(na * nb, 1e-9)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", default=C)
    ap.add_argument("--out", default="")
    # 🔴 NEAR-DUPLICATE DETECTION IS OFF BY DEFAULT — measured failure, 2026-08-01.
    # At --near 0.80 it flagged SIX DIFFERENT YEARS of tax returns as duplicates
    # of one another (2015 vs 2017 scored 0.99; 2020/2021/2022 vs 2024 scored
    # 0.95-0.97). Tax forms are ~95% identical boilerplate: the vocabulary IS
    # the form, and the figures that distinguish them are noise in a cosine.
    # The containment guard did not save it, because different years genuinely
    # have near-identical vocabulary AND near-identical length.
    # It reported 53.9% of the corpus as redundant. The true exact-duplicate
    # figure is ~13%. A method that quadruples its own answer is not a method.
    # Exact hashing is provable and stays on. Anything else must be asked for
    # explicitly, and every drop must be read by a human before it is trusted.
    ap.add_argument("--near", type=float, default=0.0,
                    help="0 disables near-duplicate detection (default). "
                         "Values <0.995 have produced false positives on this corpus.")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--move-dupes", action="store_true",
                    help="move the older copies into CORPUS\\DUPES\\ , keeping the NEWEST "
                         "of each identical set in the corpus. Moves only — never deletes.")
    a = ap.parse_args()
    root = a.corpus
    out = a.out or os.path.join(root, "_ALL_TEXT_DEDUPED.md")

    files = sorted(f for f in os.listdir(root)
                   if f.endswith(".txt") and not f.startswith("_"))
    text = {}
    bags = {}
    for f in files:
        t = read_norm(os.path.join(root, f))
        if not t:
            continue
        text[f] = t
        bags[f] = bag(t)

    # ---- 1. exact ----------------------------------------------------------
    groups = collections.defaultdict(list)
    for f, t in text.items():
        groups[hashlib.sha256(t.lower().encode()).hexdigest()].append(f)
    keep = []
    dropped = []
    for _, v in groups.items():
        # KEEP THE NEWEST — Keith's rule, 2026-08-01. The first version sorted
        # by (-length, name), which for BYTE-IDENTICAL files degenerates to
        # alphabetical: it silently kept whichever name sorted first. That is a
        # selection rule that looks principled and is arbitrary.
        v.sort(key=lambda f: -os.path.getmtime(os.path.join(root, f)))
        keep.append(v[0])
        for d in v[1:]:
            dropped.append((d, v[0], "exact"))

    # ---- 2/3. near-duplicate containment ----------------------------------
    keep.sort(key=lambda f: -len(text[f]))
    final = []
    if a.near <= 0:
        final = keep
        print("  near-duplicate detection: OFF (exact hashing only — see the note "
              "in --near; it flagged six different tax years as duplicates)")
    else:
        print("  ⚠ near-duplicate detection ON at %.3f — READ EVERY DROP BELOW. "
              "This has produced false positives on this corpus." % a.near)
        for f in keep:
            redundant = None
            for g in final:
                c = cos(bags[f], bags[g])
                if c >= a.near and sum(bags[f].values()) <= sum(bags[g].values()) * 1.05:
                    shared = len(set(bags[f]) & set(bags[g])) / max(len(set(bags[f])), 1)
                    if shared >= 0.70:
                        redundant = (g, c)
                        break
            if redundant:
                dropped.append((f, redundant[0], "near %.2f" % redundant[1]))
            else:
                final.append(f)

    print("  corpus files        : %d" % len(files))
    print("  kept (distinct)     : %d" % len(final))
    print("  dropped as duplicate: %d" % len(dropped))
    ch_keep = sum(len(text[f]) for f in final)
    ch_drop = sum(len(text[f]) for f, _, _ in dropped)
    print("  chars kept          : {:,}".format(ch_keep))
    print("  chars de-duplicated : {:,}  ({:.1f}%)".format(ch_drop, 100 * ch_drop / max(ch_keep + ch_drop, 1)))
    print("\n  --- every drop, for review ---")
    for d, k, why in sorted(dropped, key=lambda x: -len(text[x[0]]))[:40]:
        print("   %-58s  <- %-8s dup of  %s" % (d[:58], why, k[:44]))

    if a.move_dupes and not a.dry_run:
        import shutil
        dd = os.path.join(root, "DUPES")
        os.makedirs(dd, exist_ok=True)
        moved = failed = 0
        log = []
        for d, k, why in dropped:
            if why != "exact":
                continue                      # only ever move PROVEN duplicates
            s = os.path.join(root, d)
            t = os.path.join(dd, d)
            try:
                if os.path.exists(t):
                    failed += 1
                    continue
                shutil.move(s, t)
                moved += 1
                log.append("%s\t-> DUPES\\  (identical to %s, which is newer)" % (d, k))
            except Exception as e:                                  # noqa: BLE001
                failed += 1
                print("   SKIP %s (%s)" % (d[:60], str(e)[:60]))
        with open(os.path.join(dd, "_WHY_THESE_ARE_HERE.md"), "w", encoding="utf-8") as fh:
            fh.write("# DUPES — byte-identical copies moved out of the corpus\n\n")
            fh.write("Moved %s by `BTS_MESH\\dedupe_corpus.py --move-dupes`.\n\n"
                     % datetime.now().strftime("%Y-%m-%d %H:%M"))
            fh.write("Each file here is **byte-identical**, after normalisation, to a file still in\n"
                     "`CORPUS\\`. The copy KEPT is the one with the newest modification time.\n"
                     "Nothing was deleted; move any of these back if a selection is wrong.\n\n")
            fh.write("⚠ Only EXACT duplicates were moved. Near-duplicate detection is off by\n"
                     "default: at 0.80 cosine it flagged six different tax years as duplicates of\n"
                     "one another, because tax forms are ~95%% identical boilerplate.\n\n")
            fh.write("| moved | reason |\n|---|---|\n")
            for line in log:
                a_, b_ = line.split("\t", 1)
                fh.write("| `%s` | %s |\n" % (a_, b_))
        print("\n  moved to DUPES\\ : %d" % moved)
        if failed:
            print("  could not move   : %d" % failed)
        print("  note written     : DUPES\\_WHY_THESE_ARE_HERE.md")

    if a.dry_run:
        print("\n  DRY RUN — nothing written. Nothing is ever deleted by this tool.")
        return 0

    with open(out, "w", encoding="utf-8") as fh:
        fh.write("# LEGAL CORPUS — DE-DUPLICATED\n")
        fh.write("# generated %s by BTS_MESH\\dedupe_corpus.py\n" %
                 datetime.now().strftime("%Y-%m-%d %H:%M"))
        fh.write("# %d of %d corpus files; %d duplicates excluded; %s chars\n" %
                 (len(final), len(files), len(dropped), "{:,}".format(ch_keep)))
        fh.write("# NOTHING WAS DELETED — every source .txt remains in CORPUS\\.\n\n")
        for f in sorted(final):
            fh.write("\n\n=================== %s ===================\n\n" % f)
            fh.write(text[f])
    print("\n  written: %s (%s bytes)" % (out, "{:,}".format(os.path.getsize(out))))
    return 0


if __name__ == "__main__":
    sys.exit(main())
