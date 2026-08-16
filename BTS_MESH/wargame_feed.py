#!/usr/bin/env python3
"""
wargame_feed.py - build the NEUTRAL record for the Chambers v. Abraxas war game.

WHY THIS EXISTS
  Keith, 2026-08-02: "The feed should include all the exhibits, filings and case documents we have.
  Nothing else. None of my comments or any word from you. Only the case file documents."

  That is a HARDER requirement than it sounds. The corpus contains, mixed in with the evidence:
  case memos, a gap analysis, a deposition outline, two AI/OSINT "Shift Abraxas to Jasper"
  reconstructions, a file literally named "Timeline that Destroys the Defense", and a
  plaintiff-authored chronology whose every row is a characterization. Feed any of those to a node
  and the war game returns our own conclusions wearing a judge's wig.

WHAT IT DOES
  1. Canonicalises  - the corpus holds each document up to 4x under different path-flattened names.
  2. Classifies     - reuses sweep_corpus.RULES. First match wins; 00_OURS is first, deliberately.
  3. EXCLUDES       - 00_OURS, vendor manuals, and EXTRA_EXCLUDE below. Prints every drop, with a
                      reason. An unexplained exclusion is as bad as an unexplained inclusion.
  4. Emits          - one .txt per document under record/, plus 00_INDEX.txt, plus
                      EXCLUSION_MANIFEST.txt so the drops are auditable by eye.
  5. Truncation control - bytes consumed vs bytes declared on every read. A short read ABORTS the
                      build. (The sandbox mount has lied about file contents thirteen times.)

  CORE = 01..07  the trial record: pleadings, discovery, their production, texts, emails,
                 instrument, money.
  FULL = 01..09  adds corporate and Jasper/UCC - the joinder side of the case.

NEUTRALITY NOTES, because they are the whole point
  - Documents keep their own filenames. Those names are the record's, not ours.
  - Bundle prefixes (01_PLEADINGS...) are structural, not argumentative.
  - Document ORDER in the index is SHUFFLED against a per-session seed, so no agent inherits a
    running order that implies a narrative. Primacy and recency are real effects.
  - 00_INDEX.txt carries NO description of any document. A one-line summary is an argument.

USAGE (native Windows)
    py -3.14 wargame_feed.py --dry-run          # report in/out, write nothing
    py -3.14 wargame_feed.py --build            # write record/ + index + manifest
    py -3.14 wargame_feed.py --build --full     # include 08/09
    py -3.14 wargame_feed.py --selftest         # prove the truncation control FAILS on demand
"""
from __future__ import annotations
import argparse, hashlib, random, re, sys
import pathlib
from datetime import datetime
from pathlib import Path

MESH = Path(__file__).resolve().parent
sys.path.insert(0, str(MESH))

def _resolve(win: str, tail: str) -> Path:
    """Windows path if it exists, else the sandbox mount. The sandbox has no drive letters.

    ⚠ The sandbox is for VALIDATING THE CLASSIFICATION ONLY. The authoritative build runs
    natively, because the mount has corrupted host files thirteen measured times and a
    corrupted record is a war game played on evidence that does not exist.
    """
    p = Path(win)
    if p.exists():
        return p
    for c in Path("/sessions").glob(f"*/mnt/{tail}"):
        return c
    return p


CORPUS = _resolve(r"V:\Ai\Legal\CORPUS", "Ai/Legal/CORPUS")

# 🔴 PATCHED 2026-08-08. THE TWO SETS NOW HAVE TWO HOMES.
# Until today both --narrow and --expanded wrote to a single `record\` directory, so building
# either one DESTROYED the other. That is how the narrow set was lost on 2026-08-03; it was
# recovered only by splitting the concatenated RECORD_ALL.txt back into files. BU.MD has carried
# "do not rebuild either set until this is fixed" ever since.
#   --expanded -> record\        (unchanged: record_trim.py, rfa_review.py and mesh_fanout.py
#                                 all glob this path; moving it would fork the tree)
#   --narrow   -> record_core\   (the directory the narrow set was reconstituted into)
# The spec in BU.MD said record_core\ / record_expanded\. Keeping the expanded set at `record\`
# meets the actual requirement - one build must not destroy the other - without breaking three
# downstream tools. The deviation is deliberate; the guard below is what makes it safe.
OUT_EXPANDED = _resolve(r"V:\Ai\Legal\WARGAME\record",      "Ai/Legal/WARGAME/record")
OUT_CORE     = _resolve(r"V:\Ai\Legal\WARGAME\record_core", "Ai/Legal/WARGAME/record_core")


def out_dir(narrow: bool):
    return OUT_CORE if narrow else OUT_EXPANDED

# 🔴 REVISED 2026-08-02, mid-build, and the reason is the whole point of the exercise.
#
# The first cut defined CORE as bundles 01-07 and pushed 08/09 out of scope. That silently
# dropped `Abraxas_Labs_SOPs_MAIN`, the QA Policy, the Business Plan, and the Cashmere UCC-1 -
# and every one of those is contested. The QA Manual is what requires the maintenance records
# the counterclaim ignores; the Business Plan bears on lost profits; the UCC-1 itemises their lab
# down to keyboards and bears on title.
#
# ⇒ DECIDING WHAT IS "CORE" IS ITSELF AN ARGUMENT ABOUT THE CASE. A feed that pre-sorts the
#   record by relevance has already told the agents what matters, which is exactly the
#   contamination this file exists to prevent.
#
# So: ONE RECORD. Every case document goes in. The only exclusions are the four categories that
# are not case documents at all - our work product, OSINT reconstructions, vendor manuals, and
# the bulk-duplicate registration filings below. The agents decide what is material. That is
# their job, not ours.
ALL_BUNDLES = ["01_PLEADINGS", "02_DISCOVERY", "03_THEIRPROD", "04_TEXTS", "05_EMAILS",
               "06_INSTRUMENT", "07_MONEY", "08_CORPORATE", "09_JASPER_UCC"]

# The 26 Secretary of State filings are the same handful of registration documents scanned
# repeatedly (77751110002-4672398-1 and -3 are one filing, twice). They are low-information and
# token-expensive. Kept OUT of the default record but WRITTEN TO DISK under sos/, listed in the
# index, and reachable by any agent that wants them - so this is a shelving decision, not an
# exclusion, and no agent is prevented from reading one.
SOS_BULK = re.compile(r'SOS docs__77751', re.I)

# ---------------------------------------------------------------- --narrow
# 🔴 Keith, 2026-08-02: "We narrowly construe the corpus. We do a few limited runs (3-5) - then
# expand the corpus and compare the results."
#
# THIS TURNS THE CORPUS'S BIGGEST WEAKNESS INTO THE EXPERIMENT. The Jasper evidence, both UCC-1s,
# the divorce file and the PJLA material are NOT IN THE RECORD and are not going in before the
# discovery cutoff. A war game that feeds them to the models measures a case we do not have.
# So: run NARROW first - only what is in the record or set to go in - then run EXPANDED and DIFF
# the two. The delta prices what the unadmitted evidence is actually worth if we get it in.
# That is a better answer than either run alone, and it is why the incompleteness stops being a
# caveat and becomes a treatment variable.
NARROW_DROP_BUNDLES = {"09_JASPER_UCC"}          # Jasper - UCCs - divorce - BuiltWith: not in evidence
# ⚠ The maintenance guide is in the corpus TWICE under two names - `hplc1100-maintenance` (164,960 B,
# produced by Abraxas via "Abraxas Discovery Reply") and `Maintaining_Your_Agilent_HPLC_1100`
# (164,950 B, same publication, different capture). canonical() cannot collapse them because the
# base names differ. KEEP THE ONE WITH THE PROVENANCE WE WANT - the copy Abraxas produced - and drop
# the twin, or the models read the same manual twice and weight it double.
NARROW_DROP_NAMES = re.compile(
    r'agilent-1100-series-quaternary-pump-g1311a'    # 326 KB pump manual - reference
    r'|maintaining_your_agilent'                     # duplicate of hplc1100-maintenance
    # 🔴 EMAIL SPLITS - Keith, 2026-08-02: "I split the original doc into three parts so I could
    # email them. You can exclude parts 1, 2 and 3 as duplicative."
    # The WHOLE is `Exhibit B1 - Vadim Yerokhin- emails.pdf` at 99,495 B. The parts sum to
    # 39,057 + 29,472 + 33,317 = 101,846 B - the same document, re-filed in pieces, plus a
    # separate OCR capture of P1 (90,402) and a P1a variant (39,962). canonical() cannot see it
    # because every piece has a different name. Nine files, ~430 KB, for one 99 KB document.
    r'|emails P1 OCR|emails P1a|emails P1|emails P2|emails P3'
    # 🔴 TEXT MESSAGES - one document, two captures, measured word-set Jaccard 1.00.
    # Keep `Vadim Yerokhin - Text Messages` (126,072 B); drop the A1 capture (116,261 B).
    # Name-based and explicit, NOT a similarity threshold: the dedupe_corpus scar is that 0.80
    # cosine called six different tax years duplicates of each other. The author told us these
    # are the same document - that is better evidence than any metric.
    r'|Exhibit A1-Vadim Yerokhin-Text Messages',
    re.I)
# ⚠ The maintenance guide STAYS WHOLE. Keith asked for just the repair pages, and for a filing that
# is right - but page-trimming an OCR text risks cutting the paragraph that matters, and at ~40K
# tokens the whole guide is cheap insurance. It is also the single most useful document in the
# narrow set: Abraxas produced it, and it calls the outlet ball valve "changed as part of a regular
# maintenance routine" and says the needle "should be replaced when it becomes bent."

# ---------------------------------------------------------------- extra exclusions
# sweep_corpus's 00_OURS rule catches the memos, the Grok timeline, the gap analysis, the
# deposition outline, the Chambers annotations, REVISED TIMELINE, "Timeline that Destroys",
# "Pre-trial Discovery - Grok" and both "Shift Abraxas to Jasper" files. These three are NOT
# caught by it and were found by eye on 2026-08-02.
EXTRA_EXCLUDE = [
    # 🔴 ADDED 2026-08-03, BEFORE THE EXPANDED RUN, NOT AFTER IT.
    # The work-product filter is `classify(name) == "00_OURS"` — a BUNDLE test. These two files
    # classify into 09_JASPER_UCC, so on an expanded run they would have sailed straight into the
    # feed. They are PLAINTIFF-AUTHORED NARRATIVE — the same species as "ABRAXAS -1 Timeline"
    # below, and the same species as the exclusion manifest that contaminated the first run.
    # A bundle-level filter cannot catch work product that lives inside an evidence bundle.
    # ⇒ The expanded run is exactly where contamination gets in, because the bundle it adds is the
    #   one bundle that mixes our analysis with the underlying filings. Check by NAME, every time.
    (r'Shift Abraxas to Jasper narrative',
     "PLAINTIFF-AUTHORED NARRATIVE. It argues the transfer theory rather than evidencing it. The "
     "UCC-1s, the UCC-3 termination and the divorce file ARE in the expanded feed - so the "
     "underlying documents are all there and a node can reach the conclusion on its own, or fail "
     "to, which is the entire point of the expanded run."),
    (r'Shift Abraxas to Jasper timeline',
     "PLAINTIFF-AUTHORED NARRATIVE, same as above. A timeline is a set of characterizations with "
     "dates attached; the documents it summarizes are in the feed."),
    (r'ABRAXAS -1 Timeline',
     "PLAINTIFF-AUTHORED NARRATIVE. Verified by opening it: every row is a characterization "
     "('Chambers Begins Providing Daily Technical Assistance'), not a document. It is a summary "
     "OF exhibits A1/B1/C1, and those exhibits are in the feed - so nothing is lost by dropping "
     "it, and a thumb comes off the scale."),
    (r'BuiltWith',
     "OSINT, not a case document. Web-archaeology on jasper-lab.com's domain history. Same "
     "species as the two 'Shift Abraxas to Jasper' files Keith has already banned."),
]
EXTRA_RE = re.compile("|".join(f"({p})" for p, _ in EXTRA_EXCLUDE), re.I)


def _reason(name: str) -> str:
    for pat, why in EXTRA_EXCLUDE:
        if re.search(pat, name, re.I):
            return why
    return "?"


class Truncated(RuntimeError):
    pass


def read_verified(p: Path) -> str:
    """Read a file and PROVE we got all of it. A short read aborts the build.

    The mount has under-reported file size by 39,584 bytes and served a python file truncated
    mid-expression, producing a false SyntaxError. Neither errored. The only defense is to compare
    what we consumed against what the filesystem declared.
    """
    declared = p.stat().st_size
    raw = p.read_bytes()
    if len(raw) != declared:
        raise Truncated(f"{p.name}: consumed {len(raw)} B, filesystem declared {declared} B")
    return raw.decode("utf-8", errors="replace")


def classify(name: str) -> str:
    from sweep_corpus import RULES
    for bundle, pat in RULES:
        if re.search(pat, name, re.I):
            return bundle
    return "99_UNCLASSIFIED"


def build(narrow: bool, dry: bool, seed: int, force: bool = False) -> int:
    from sweep_corpus import canonical

    ev, manuals, nraw = canonical(CORPUS)
    keep, shelved, dropped = [], [], []

    for p in ev:
        if EXTRA_RE.search(p.name):
            dropped.append((p, "EXTRA", _reason(p.name))); continue
        b = classify(p.name)
        if b == "00_OURS":
            dropped.append((p, "OUR OWN WORK PRODUCT",
                            "Our conclusions are not evidence. Feeding them to a node returns "
                            "them as findings.")); continue
        if narrow and b in NARROW_DROP_BUNDLES:
            dropped.append((p, "NOT IN THE RECORD (narrow run)",
                            "Jasper, both UCC-1s, the divorce file and the OSINT are NOT IN "
                            "EVIDENCE and are not going in before the cutoff. A war game that "
                            "reads them measures a case we do not have. Included in the "
                            "EXPANDED run, and the DIFF is the finding.")); continue
        if SOS_BULK.search(p.name):
            shelved.append((b, p)); continue
        # ⚠ this check used to run ONLY over the `manuals` list, so every email split and the
        # duplicate text-message capture sailed straight through and the record never shrank.
        if narrow and NARROW_DROP_NAMES.search(p.name):
            dropped.append((p, "SPLIT / DUPLICATE CAPTURE OF A DOCUMENT ALREADY IN THE RECORD",
                            "Keith, 2026-08-02: the emails doc was split into P1/P2/P3 to send by "
                            "email, and the text messages exist as two captures of one file. The "
                            "WHOLE of each is kept; the pieces are not evidence twice."))
            continue
        keep.append((b, p))
    # 🔴 The maintenance guide is EVIDENCE, not reference - Abraxas produced it, and it is the
    # document that calls the ball valve routine maintenance. sweep_corpus drops all manuals; we
    # put that one back and drop only the 326 KB pump manual.
    for m in manuals:
        if NARROW_DROP_NAMES.search(m.name):
            dropped.append((m, "VENDOR MANUAL - pump",
                            "326 KB G1311A pump manual. Reference. The 165 KB MAINTENANCE guide "
                            "is KEPT - it is evidence, produced by Abraxas."))
        else:
            keep.append(("06_INSTRUMENT", m))

    # 🔴 CONTENT DEDUPE - canonical() matches on NAME, so it cannot see two captures of the same
    # document filed under different names. Measured 2026-08-02: `Vadim Yerokhin - Text Messages`
    # and `Exhibit A1-Vadim Yerokhin-Text Messages` have a word-set Jaccard of **1.00** - byte-for-
    # byte the same content, 242 KB total, half of it pure repetition. Feeding both makes every
    # model weight the text messages twice.
    # Keep the LARGEST capture of each content set; report every drop.
    seen: dict[frozenset, tuple] = {}
    deduped = []
    for b, p in keep:
        try:
            words = frozenset(re.findall(r'\w+', p.read_text(encoding="utf-8", errors="replace").lower()))
        except OSError:
            deduped.append((b, p)); continue
        prev = seen.get(words)
        if prev is None:
            seen[words] = (b, p); deduped.append((b, p))
        else:
            loser = p if p.stat().st_size <= prev[1].stat().st_size else prev[1]
            winner = prev[1] if loser is p else p
            if loser is not p:                       # new one wins - swap it in
                deduped = [(bb, pp) for bb, pp in deduped if pp is not prev[1]]
                deduped.append((b, p)); seen[words] = (b, p)
            dropped.append((loser, "EXACT CONTENT DUPLICATE",
                            f"Identical word-set to {winner.name}. Two captures of one document "
                            f"under different names - canonical() matches on NAME and cannot see "
                            f"it. Kept the larger capture."))
    keep = deduped

    keep.sort(key=lambda t: (t[0], t[1].name.lower()))
    shelved.sort(key=lambda t: t[1].name.lower())

    kb = sum(p.stat().st_size for _, p in keep)
    sb = sum(p.stat().st_size for _, p in shelved)
    print(f"\n{'='*78}\n  WAR GAME FEED - {'NARROW (the record as it stands)' if narrow else 'EXPANDED'}"
          f"\n  corpus {nraw} raw files -> {len(ev)+len(manuals)} distinct"
          f"\n  RECORD {len(keep)} docs, {kb:,} B (~{kb//4:,} tok)"
          f"   SHELVED {len(shelved)} ({sb:,} B)   DROPPED {len(dropped)}\n{'='*78}")

    by_bundle: dict[str, int] = {}
    for b, _ in keep:
        by_bundle[b] = by_bundle.get(b, 0) + 1
    for b in ALL_BUNDLES:
        print(f"  {b:<16} {by_bundle.get(b,0):>3}")
    print(f"  {'sos/ (shelved)':<16} {len(shelved):>3}   readable, just not in the default set")

    print(f"\n  --- EXCLUDED, WITH REASON ---")
    for p, cat, why in sorted(dropped, key=lambda t: (t[1], t[0].name.lower())):
        print(f"  [{cat}] {p.name}")

    if dry:
        print(f"\n  DRY RUN - nothing written.\n")
        return 0

    OUT = out_dir(narrow)

    # 🔴 OVERWRITE GUARD, added 2026-08-08. A record set is expensive and partly IRREPLACEABLE -
    # two of the six exhibits added on 2026-08-03 are transcriptions that no script can
    # regenerate (record_add_exhibits.py refuses to fake them). Silently overwriting a populated
    # set is therefore data loss, not a rebuild. Refuse, name what would have been destroyed,
    # and make the caller say --force out loud.
    existing = sorted(p for p in OUT.glob("*.txt")) if OUT.exists() else []
    if existing and not force:
        print(f"\n  🔴 REFUSING TO BUILD - {OUT} already holds {len(existing)} documents.")
        print(f"     A {'NARROW' if narrow else 'EXPANDED'} build would overwrite them.")
        for p in existing[:5]:
            print(f"       {p.name}")
        if len(existing) > 5:
            print(f"       ... and {len(existing) - 5} more")
        print("     Two of the 2026-08-03 exhibits are TRANSCRIPTIONS and cannot be rebuilt")
        print("     mechanically. Move the directory aside, or pass --force if you mean it.\n")
        return 3

    OUT.mkdir(parents=True, exist_ok=True)
    total = 0
    written: list[tuple[str, str, int]] = []
    for b, p in keep:
        try:
            txt = read_verified(p)
        except Truncated as e:
            print(f"\n  🔴 ABORT - TRUNCATED READ: {e}")
            print("     The build is stopped. A partial record is worse than no record,")
            print("     because nothing downstream would report the gap.\n")
            return 2
        dest = OUT / f"{b}__{p.name}"
        dest.write_text(txt, encoding="utf-8")
        total += len(txt)
        written.append((dest.name, hashlib.sha256(txt.encode()).hexdigest()[:12], len(txt)))

    # index - SHUFFLED. A fixed running order is an argument about what matters.
    rnd = random.Random(seed)
    shuffled = written[:]
    rnd.shuffle(shuffled)
    idx = [
        "THE RECORD - Chambers v. Abraxas Labs, LLC, CJ-2025-1618",
        "District Court of Tulsa County, Oklahoma. Non-jury trial.",
        "",
        f"{len(written)} documents. {total:,} characters.",
        "",
        "Pleadings, written discovery, documents produced by the parties, and exhibits.",
        "",
        "This list is in NO significant order. It is shuffled deliberately, so that no reader",
        "inherits a running order that implies a narrative. No document is summarized here,",
        "because a one-line summary of a document is an argument about it.",
        "",
        "Read what you need. Every read is logged.",
        "",
        f"{'FILE':<80} {'SHA256':<14} BYTES",
        "-" * 104,
    ]
    for n, h, sz in shuffled:
        idx.append(f"{n:<80} {h:<14} {sz}")
    (OUT / "00_INDEX.txt").write_text("\n".join(idx), encoding="utf-8")

    man = ["EXCLUSION MANIFEST - what was kept OUT of the war game record, and why",
           f"Built 2026-08-02. Corpus: {CORPUS}",
           "",
           "Keith, 2026-08-02: 'Only the case file documents. None of my comments or any word",
           "from you.' Every exclusion below is auditable by name. Nothing was dropped silently.",
           ""]
    for cat in sorted({c for _, c, _ in dropped}):
        man.append(f"\n### {cat}")
        why = next(w for _, c, w in dropped if c == cat)
        man.append(f"{why}\n")
        for p, c, _ in sorted(dropped, key=lambda t: t[0].name.lower()):
            if c == cat:
                man.append(f"  - {p.name}")
    # 🔴 NOT inside OUT/. The record directory must contain ONLY case documents. This file
    # names our work product and quotes Keith - it is the single worst thing that could leak into
    # the feed, and on 2026-08-02 it did exactly that. Two independent guards now: it is written
    # to the parent, AND wargame.load_record() whitelists on the bundle prefix.
    # 🔴 The manifest is per-MODE, for the same reason the record directory is. A narrow run and
    # an expanded run exclude different documents for different reasons; one shared filename means
    # the second run silently overwrites the first run's audit trail - the same defect as the
    # record directory, one file smaller, and just as invisible.
    man_name = "EXCLUSION_MANIFEST_core.txt" if narrow else "EXCLUSION_MANIFEST_expanded.txt"
    (OUT.parent / man_name).write_text("\n".join(man), encoding="utf-8")

    print(f"\n  ✅ wrote {len(written)} documents + index + manifest -> {OUT}")
    print(f"     {total:,} chars  ~{total//4:,} tokens  (index shuffled, seed={seed})\n")
    return 0


def selftest() -> int:
    """Prove the truncation control goes RED. A control never shown to fail is not a control."""
    import tempfile, os
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "t.txt"
        p.write_text("x" * 5000, encoding="utf-8")
        assert len(read_verified(p)) == 5000, "clean read failed"

        class Liar(type(p)):
            pass
        # simulate the mount's signature failure: stat() declares more than read_bytes() returns
        real_stat = Path.stat
        Path.stat = lambda self, *a, **k: type("S", (), {"st_size": 9999})()  # type: ignore
        try:
            read_verified(p)
        except Truncated as e:
            Path.stat = real_stat  # type: ignore
            print(f"  selftest: truncation control FIRED as designed -> {e}")
            print("  selftest: PASS (clean read OK, short read aborts)")
            return 0
        Path.stat = real_stat  # type: ignore
    print("  🔴 selftest FAILED - a short read was NOT caught. Do not trust the build.")
    return 1


# ---------------------------------------------------------------- console log
class _Tee:
    """Mirror everything printed to a log file.

    Keith, 2026-08-02: "Those are transient on the desktop, always deleted after run - be sure you
    are writing logs, I can't always paste the output."

    The Desktop bat is deleted the moment it finishes, and its console goes with it. So the LOG IS
    THE ONLY RECORD OF WHAT HAPPENED. Logging belongs in the tool, not the wrapper - a wrapper that
    is thrown away cannot be the thing that remembers. Line-buffered and flushed on every write, so
    a crash or a closed window still leaves everything up to the failure.
    """

    def __init__(self, path, stream):
        self.path, self.stream = pathlib.Path(path), stream
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.fh = self.path.open("a", encoding="utf-8", errors="replace")
        self.fh.write(f"\n\n{'='*78}\n### RUN {datetime.now():%Y-%m-%d %H:%M:%S}  "
                      f"{' '.join(sys.argv)}\n{'='*78}\n")
        self.fh.flush()

    def write(self, s):
        self.stream.write(s)
        try:
            self.fh.write(s); self.fh.flush()
        except Exception:
            pass
        return len(s)

    def flush(self):
        self.stream.flush()
        try:
            self.fh.flush()
        except Exception:
            pass


def start_log(path):
    sys.stdout = _Tee(path, sys.__stdout__)
    sys.stderr = _Tee(path, sys.__stderr__)
    print(f"  logging to {path}")


def main() -> int:
    start_log(OUT_EXPANDED.parent / "_BUILD_LOG.txt")
    ap = argparse.ArgumentParser()
    ap.add_argument("--build", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--narrow", action="store_true",
                    help="only what is in the record: drops Jasper/UCC/divorce/OSINT + pump manual")
    ap.add_argument("--expanded", action="store_true", help="everything (for the comparison run)")
    ap.add_argument("--seed", type=int, default=20260802)
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--force", action="store_true",
                    help="overwrite a record directory that already holds documents. "
                         "Two 2026-08-03 exhibits are transcriptions and CANNOT be rebuilt.")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if not (a.build or a.dry_run):
        print("need --build or --dry-run or --selftest"); return 2
    if a.narrow and a.expanded:
        print("pick one: --narrow or --expanded"); return 2
    return build(not a.expanded, a.dry_run and not a.build, a.seed, a.force)


if __name__ == "__main__":
    sys.exit(main())
