#!/usr/bin/env python3
"""
sweep_corpus.py — run SGH and GEM adversarially over an entire document corpus.

WHY THIS EXISTS
  Cowork's Linux sandbox caps a bash call at 45 s. Measured 2026-08-01: a 29 KB slice to
  gemini-2.5-pro took 32.2 s; 119 KB and 165 KB slices BOTH TIMED OUT. So a full-corpus sweep
  cannot run from the sandbox at all. It runs natively, here, where there is no ceiling.

WHAT IT DOES, IN ORDER
  1. CANONICALISE. The corpus holds the same document under several path-prefixed names
     ("Abraxas Case__X.txt" and "X.txt"). `dedupe_corpus.py` removed only BYTE-IDENTICAL copies,
     and its near-duplicate mode is OFF by default (it once called six tax years duplicates of
     each other). Measured on the legal corpus: 141 files -> 105 distinct documents; the text
     messages appear FOUR times. Feeding the raw set weights those documents 2-4x.
  2. DROP VENDOR MANUALS. ~680 KB of Agilent service manuals are reference, not evidence.
  3. DROP OUR OWN WORK PRODUCT. Case memos, timelines, gap analyses and deposition outlines are
     OUR CONCLUSIONS. Feeding them back to a node produces agreement, not findings. This is the
     single most important exclusion in the file.
  4. BUNDLE by document class, with a TRUNCATION CONTROL on every read (bytes consumed vs bytes
     declared by stat). A short read is a hard failure, never a quiet one.
  5. ASK both nodes the same adversarial question set per bundle; write every return to disk.
     Resumable: an existing non-empty return file is skipped, so a crash costs one bundle.

USAGE (native Windows)
    py -3.14 sweep_corpus.py                       # full sweep, both nodes
    py -3.14 sweep_corpus.py --bundles-only        # build + report, spend nothing
    py -3.14 sweep_corpus.py --node gem            # one node
    py -3.14 sweep_corpus.py --selftest            # prove the truncation control FAILS on demand
"""
from __future__ import annotations
import argparse, collections, json, os, re, sys, time
from pathlib import Path

WIN_CORPUS = Path(r"V:\Ai\Legal\CORPUS")
WIN_OUT    = Path(r"V:\Ai\Legal\NODE_SWEEP")
MESH       = Path(__file__).resolve().parent


def _resolve(p: str | None, default: Path) -> Path:
    if p:
        return Path(p)
    if default.exists():
        return default
    for c in Path("/sessions").glob("*/mnt/Ai/Legal/CORPUS"):   # sandbox fallback
        if "CORPUS" in default.name or default.name == "CORPUS":
            return c
    return default


# ---------------------------------------------------------------- classification
# First match wins, so order matters. OURS must come first: several of our own memos
# mention every keyword that would otherwise route them into an evidence bundle.
RULES = [
    ("00_OURS", r'Case Summary Memo|Grok TimeLine|Issue and Discovery Gap|Deposition Outline'
                r'|Chambers First Reply|Notes by Chambers|Notes to Abraxas production'
                r'|Discovery Request_Chambers|REVISED TIMELINE|Timeline that Destroys'
                r'|Pre-trial Discovery - Grok|Shift Abraxas to Jasper|Abraxas Production Notes'),
    ("01_PLEADINGS",  r'Petition|Answer to Plaintiff|motion to dismiss|reply to defendants counterclaim'
                      r'|1054406750|1054912040|CASE_No_CJ-2023|Lease Agreement'),
    ("02_DISCOVERY",  r'Discovery Request|Response to Discovery|Abraxas Production\.pdf|John Farley'
                      r'|Discovery Requests to Plaintiff'),
    ("03_THEIRPROD",  r'PRODUCTION DOCS'),
    ("04_TEXTS",      r'Text Messages'),
    ("05_EMAILS",     r'emails|\.eml'),
    ("06_INSTRUMENT", r'Instrument Test Data|Instrument Data|ORACL|GenTech|Agilent'
                      r'|ABRAXAS -1 Timeline|OPEN for Testing'),
    ("07_MONEY",      r'Invoice|Scan of check|Check |Accts Recievable|reciept|Receipt|Payment for'),
    ("08_CORPORATE",  r'SOS docs|Business_Plan|SOPs|QA Policy|77751'),
    ("09_JASPER_UCC", r'Jasper|UCC|Cashmere|Calahan|BuiltWith|M-V Divorce|Divorce Settlement|MVD-'),
]
MANUALS = re.compile(r'agilent-1100-series|maintaining_your_agilent|hplc1100-maintenance', re.I)
STRIP   = ["Abraxas Case__", "Abraxas-Exhibits__", "Abraxas Discovery Reply__",
           "Court Filings__", "Vadim Emails__"]

# 🔴 Bundles the nodes must NEVER see. Our own conclusions are not evidence.
EXCLUDE_FROM_NODES = {"00_OURS"}


# 🔴 CONTAMINATION FENCE — added 2026-08-02 after `OCR the legal backlog.bat` walked past the
# Abraxas case and OCR'd the ENTIRE D:\LEGAL tree into the corpus: 115 files of tax returns, bank
# statements, police reports, an estate, a credit report and a 1,309-page Delta Therapeutics
# application. None of it is case evidence, and a node sweep would have paid four model families to
# read Keith's W-9s. Segregation by subdirectory is not enough — the OCR writer FLATTENS paths into
# `PARENT__FILE.txt`, so a foreign document lands at the top level looking native.
# ⇒ Exclude by NAME PATTERN, at the source, and PRINT WHAT WAS DROPPED. (PLM-34.)
FOREIGN_PREFIX = ("TAXES__", "Police Reports 2024__", "Margie__", "SOS Paperwork__",
                  "DeltaTherapeutics__", "Chambers ID_Docs_files__", "M-V Divorce__")
FOREIGN_EXACT = {"ADOBE ACROBAT CANCELATION.pdf.txt", "Adobe_Chat_Transcript_1-22-25.pdf.txt",
                 "DMV ADDRESS UPDATE.pdf.txt", "Keith Chambers-CV.pdf.txt",
                 "Vyve Bill Oct-2024-needs to be revised.PDF.txt"}
# Anything carrying one of these is CASE material and is never dropped, whatever else matches.
CASE_MARKER = re.compile(r'Abraxas|Vadim|Jasper|Cashmere|Medicinal|Court Filings|Discovery Reply'
                         r'|Yerokhin|Chambers vs|CJ-202', re.I)


def _is_foreign(name: str) -> bool:
    if CASE_MARKER.search(name):
        return False                       # case marker always wins — fail safe, keep it
    return name.startswith(FOREIGN_PREFIX) or name in FOREIGN_EXACT


def canonical(corpus: Path) -> tuple[list[Path], list[Path], int]:
    """One file per distinct document, largest (most complete OCR) wins."""
    allfiles = [p for p in corpus.iterdir() if p.is_file() and p.suffix == ".txt"]
    foreign = [p for p in allfiles if _is_foreign(p.name)]
    if foreign:
        print(f"  🔴 CONTAMINATION FENCE: {len(foreign)} NON-CASE file(s) found at the top level "
              f"and EXCLUDED — move them to _NOT_ABRAXAS\\:")
        for p in foreign[:12]:
            print(f"       - {p.name}")
        if len(foreign) > 12:
            print(f"       … and {len(foreign)-12} more")
    files = [p for p in allfiles if p not in foreign]
    groups: dict[str, list[Path]] = collections.defaultdict(list)
    for p in files:
        b = p.name
        for s in STRIP:
            b = b.replace(s, "")
        b = b.replace("_FINAL_", "[FINAL]").replace("[FINAL] ", "")
        groups[re.sub(r'[^a-z0-9]', '', b.lower())].append(p)
    canon   = [max(v, key=lambda f: f.stat().st_size) for v in groups.values()]
    manuals = [p for p in canon if MANUALS.search(p.name)]
    return sorted(set(canon) - set(manuals)), manuals, len(files)


def bundle(corpus: Path, out: Path) -> dict[str, Path]:
    ev, manuals, nfiles = canonical(corpus)
    buckets: dict[str, list[Path]] = collections.defaultdict(list)
    for p in ev:
        for name, pat in RULES:
            if re.search(pat, p.name, re.I):
                buckets[name].append(p); break
        else:
            buckets["10_MISC"].append(p)

    bdir = out / "bundles"; bdir.mkdir(parents=True, exist_ok=True)
    print(f"  raw files {nfiles} -> {len(ev)+len(manuals)} distinct "
          f"({len(manuals)} vendor manuals dropped) -> {len(ev)} evidence documents")
    made, bad = {}, []
    for name in sorted(buckets):
        parts, total = [], 0
        for p in sorted(buckets[name]):
            declared = p.stat().st_size
            raw = p.read_bytes()
            if len(raw) != declared:                       # TRUNCATION CONTROL
                bad.append((p.name, declared, len(raw)))
            total += len(raw)
            parts.append(f"\n\n===== DOCUMENT: {p.name} ({len(raw)} bytes) =====\n"
                         + raw.decode("utf-8", "replace"))
        tag = "  [EXCLUDED FROM NODES — our own work product]" if name in EXCLUDE_FROM_NODES else ""
        print(f"  {name:<14} {len(buckets[name]):3d} docs {total/1024:7.0f} KB{tag}")
        f = bdir / f"{name}.txt"; f.write_text("".join(parts), encoding="utf-8")
        if name not in EXCLUDE_FROM_NODES:
            made[name] = f
    if bad:
        print("\n  🔴 TRUNCATION CONTROL FAILED — short reads, DO NOT TRUST THIS SWEEP:")
        for n, d, g in bad:
            print(f"     {n}: declared {d}, got {g}")
        sys.exit(3)
    print(f"  truncation control: {len(ev)} files, 0 short reads — CLEAN")
    return made


PROMPT = """TASK: Chambers v. Abraxas Labs, LLC, CJ-2025-1618 (Oklahoma District Court). I represent
PLAINTIFF Keith Chambers. Corporate-representative deposition 2026-08-26; discovery closes 2026-09-04.

You are reading a slice of the PRIMARY RECORD. This is not a summary and contains no analysis --
do not defer to any conclusion, because none is present. Read the documents themselves.

THE DISPUTE IN ONE PARAGRAPH: Chambers leased an Agilent 1100 HPLC to Abraxas Labs; delivery
2 June 2020. Abraxas paid a $1,500 deposit and one $535.03 installment (31 Jan 2023) and nothing
else. Abraxas counterclaims that the equipment was "non-functional due to a faulty Autosampler"
and that it gave written notice on 4 June, 1 July and 14 July 2020 and abandoned the machine on
11 Aug 2020. The lease (Exhibit C1) was never signed; Abraxas pleads that conduct and verbal
agreement supplied the terms, and that the written lease "does not constitute the entire, accurate
agreement." The lease contains no warranty clause and puts repairs on the lessee.

ALREADY ESTABLISHED, so do not re-derive it -- but DO flag anything here that contradicts it:
the 4 June "notice" is a text about an unrelated Chinese vendor (Persee); the first real written
notice is 1 July 2020; Agilent exchanged autosampler G1367A serial DE23902175 for DE23902158 on
12 Aug 2020, one day after the pleaded abandonment, and the machine ran CRMs on 15 Aug 2020.

FIND, IN THIS SLICE ONLY:
 F1. INTERNAL CONTRADICTIONS -- any place a date, amount, serial number, quantity or assertion
     collides with another in the same slice. Quote BOTH sides with their document names.
 F2. ADMISSIONS AGAINST DEFENDANT'S INTEREST -- anything by Yerokhin, Abraxas, or its counsel that
     concedes possession, use, acceptance, benefit, an obligation to pay, or the machine working.
 F3. DOCUMENTS REFERENCED BUT NOT PRESENT -- every attachment, exhibit, invoice number, service
     request, agreement or report mentioned that is NOT in this slice. These become discovery
     requests, so give the exact identifier and the document that names it.
 F4. DATES for a chronology: every dated event, with its source document. Flag any date that is
     impossible, out of order, or inconsistent with the 2 June 2020 delivery.
 F5. MONEY: every figure, invoice number, payment, balance or damages claim, with its source.
     Flag arithmetic that does not add up.
 F6. NAMES AND ENTITIES: every person or company, their role, and who they actually work for.
 F7. ADVERSE TO US -- what in this slice HELPS Abraxas. Do not soften it. If nothing, say so.
 F8. THE ONE THING a careful lawyer would notice here that a fast reader would miss.
 F9. THEORY CHANGE -- does anything here suggest the case is NOT primarily a lease-breach claim,
     or that a different or additional theory, party or remedy is available? Say so plainly, or
     write NOTHING HERE CHANGES THE THEORY.

RULES: quote verbatim with the source document name. Write "UNKNOWN" or "NOT IN THIS SLICE" rather
than guessing or inferring. Do not repeat the framing above back to me. If a finding rests on an
inference rather than a quote, label it INFERENCE and say what would confirm it. No preamble.

=== RECORD SLICE FOLLOWS ==="""


# GEM's per-task cap defaults to $0.01, which is smaller than ONE call over a 250 KB bundle.
# Measured 2026-08-01: the sweep returned bundle 1 and then refused all eight others with
# reason=PER_TASK_CAP — and because a refusal comes back ok=False with empty text rather than
# raising, it left NO artifact on disk. Two defects, one symptom: a cap set for probes, and a
# failure path that was silent. Both fixed. Keith, 2026-08-01: cost is not the constraint here.
GEM_TASK_CAP_USD = 15.00
_gem_task_started = False


def ask(node: str, text: str) -> tuple[str, dict]:
    global _gem_task_started
    sys.path.insert(0, str(MESH))
    if node == "gem" and not _gem_task_started:
        import bts_vertex
        bts_vertex.reset_task("legal_corpus_sweep", cap_usd=GEM_TASK_CAP_USD)
        _gem_task_started = True
        print(f"       [GEM task budget set to ${GEM_TASK_CAP_USD:.2f}]")
    if node == "sgh":
        import bts_sgh
        r = bts_sgh.ask(text, priority="WORK")
        out = r.get("full_text") or r.get("text") or ""
        if r.get("spilled") and r.get("path"):
            try:
                out = Path(r["path"]).read_text(encoding="utf-8", errors="replace")
            except OSError:
                pass
        return out, r
    import bts_vertex
    r = bts_vertex.ask(text)
    return r.get("text") or "", r


def selftest() -> int:
    """A control that has never been shown to fail is not a control."""
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "x.txt"; p.write_bytes(b"A" * 100)
        declared, got = p.stat().st_size, len(p.read_bytes())
        assert declared == got == 100, "clean read must pass"
        assert (declared != 90), "planted mismatch must be detectable"
        print("  selftest: truncation control detects declared != consumed — PASS")
    ev, manuals, n = canonical(_resolve(None, WIN_CORPUS))
    assert len(ev) < n, "canonicalisation must actually collapse duplicates"
    print(f"  selftest: canonicalisation collapses {n} files -> {len(ev)} evidence docs — PASS")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus"); ap.add_argument("--out")
    ap.add_argument("--node", choices=["sgh", "gem", "both"], default="both")
    ap.add_argument("--bundles-only", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()

    corpus = _resolve(a.corpus, WIN_CORPUS)
    out    = Path(a.out) if a.out else WIN_OUT
    if not corpus.exists():
        print(f"CORPUS NOT FOUND: {corpus}"); return 2
    out.mkdir(parents=True, exist_ok=True)

    print(f"\n{'='*74}\n  sweep_corpus — {corpus}\n{'='*74}")
    bundles = bundle(corpus, out)
    if a.bundles_only:
        print("\n  --bundles-only: nothing spent."); return 0

    nodes = ["sgh", "gem"] if a.node == "both" else [a.node]
    spend, done, failed = 0.0, 0, []
    print(f"\n  {len(bundles)} bundles x {len(nodes)} node(s) = {len(bundles)*len(nodes)} calls\n")
    for name, path in sorted(bundles.items()):
        body = path.read_text(encoding="utf-8", errors="replace")
        for node in nodes:
            dest = out / f"{name}__{node.upper()}.md"
            if dest.exists() and dest.stat().st_size > 400:
                print(f"  {node.upper():4} {name:<14} SKIP (already have {dest.stat().st_size} B)")
                continue
            t = time.time()
            try:
                txt, meta = ask(node, PROMPT + "\n" + body)
            except Exception as e:                     # a failure must SAY so, never leave silence
                dest.with_suffix(".FAILED.txt").write_text(f"{type(e).__name__}: {e}")
                print(f"  {node.upper():4} {name:<14} 🔴 FAILED {type(e).__name__}: {e}")
                failed.append((node, name)); continue
            if not txt.strip():
                # An empty return is a FAILURE and must leave a trace. The first version of this
                # branch printed and moved on, so eight GEM refusals vanished the moment the
                # console scrolled — the exact silent failure this file was written to prevent.
                reason = meta.get("reason") or meta.get("detail") or "no text returned"
                dest.with_suffix(".FAILED.txt").write_text(
                    f"EMPTY RETURN\nnode={node}\nbundle={name}\nok={meta.get('ok')}\n"
                    f"reason={reason}\nmeta={meta}\n", encoding="utf-8")
                print(f"  {node.upper():4} {name:<14} 🔴 EMPTY RETURN — {reason}")
                failed.append((node, name)); continue
            dest.write_text(txt, encoding="utf-8")
            c = meta.get("cost_usd") or 0.0
            spend += c; done += 1
            print(f"  {node.upper():4} {name:<14} {len(body)/1024:6.0f} KB in -> "
                  f"{len(txt):6d} chars  {time.time()-t:5.1f}s  ${c:.4f}")

    print(f"\n{'-'*74}\n  {done} returns written to {out}   spent ${spend:.4f}")
    if failed:
        print(f"  🔴 {len(failed)} FAILED, re-run to retry just those: {failed}")
    print("  ⚠ NOTHING HERE IS EVIDENCE UNTIL IT IS VERIFIED HOST-SIDE. Nodes fabricate.\n")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
