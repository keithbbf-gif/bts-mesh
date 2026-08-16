#!/usr/bin/env python3
r"""
ocr_backlog.py — turn scanned PDFs into corpus text. Resumable, time-boxed.

WHY THIS EXISTS, 2026-08-01
    `V:\Ai\Legal\CORPUS\` is built by TEXT EXTRACTION. Six core pleadings —
    the Petition, the Answer/Counterclaims, the Reply to Counterclaims, the
    Motion to Dismiss and its denial — are SCANNED IMAGES. Extraction yielded
    ~13 characters across 14 pages, so they fell out of the corpus SILENTLY.
    Nothing errored. `_ocr_queue.json` listed 0 items; they were never queued.

    Consequence: every analysis in the Legal folder, and both nodes' outputs,
    were built on a record missing its own pleadings. That is not a gap in the
    reasoning — it is a gap in the evidence the reasoning ran on.

    Measured the same day: **pdftoppm and tesseract are both present in the
    Cowork sandbox.** The backlog was never blocked on tooling, only on nobody
    checking whether the tooling was there.

DESIGN CONSTRAINTS, all measured
    * A bash call is capped at 45 s and background jobs do NOT survive it
      (PLM-25). So this is TIME-BOXED and RESUMABLE: it does what it can, then
      stops cleanly and can be re-run.
    * OCR is the expensive step, so a file that already has an output is
      skipped. Re-running is always safe.
    * A PDF with a real text layer is EXTRACTED, not OCR'd — far faster and
      more accurate. Only image-only PDFs go through tesseract.

NAMING
    Output follows the corpus convention already in use: path components under
    the root joined with `__`, then `.txt`:
        Abraxas Case/Court Filings/Petition 2025.pdf
        -> Abraxas Case__Court Filings__Petition 2025.pdf.txt

Usage
    python ocr_backlog.py --survey
    python ocr_backlog.py --under "Abraxas Case/Court Filings" --seconds 35
    python ocr_backlog.py --seconds 35            # everything still outstanding
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path

ROOT = "/sessions/bold-intelligent-mayer/mnt/LEGAL"
OUT = "/sessions/bold-intelligent-mayer/mnt/Ai/Legal/CORPUS"
MANIFEST = OUT + "/_OCR_MANIFEST.jsonl"
CACHE = "/sessions/bold-intelligent-mayer/mnt/outputs/ocr_cache"
TEXT_PER_PAGE_MIN = 120          # below this average -> treat as image-only
# 150 dpi, not 200. Measured 2026-08-01: 200 dpi ran ~7.5 s/page, which against
# a 45 s bash ceiling is ~4 pages a call and ~500 pages of backlog. 150 dpi is
# comfortably legible for typed court filings and roughly halves that.
DPI = 150


def flat_name(pdf: str) -> str:
    rel = os.path.relpath(pdf, ROOT)
    return rel.replace(os.sep, "__").replace("/", "__") + ".txt"


def has_text_layer(pdf: str):
    """(needs_ocr, npages, chars_per_page). Never raises."""
    try:
        import logging
        logging.getLogger("pypdf").setLevel(logging.ERROR)
        from pypdf import PdfReader
        r = PdfReader(pdf)
        n = len(r.pages)
        probe = min(n, 6)
        t = 0
        for pg in r.pages[:probe]:
            try:
                t += len(pg.extract_text() or "")
            except Exception:
                pass
        per = t / max(probe, 1)
        return (per < TEXT_PER_PAGE_MIN, n, per)
    except Exception:
        return (True, 0, 0.0)


def extract_text_layer(pdf: str) -> str:
    try:
        p = subprocess.run(["pdftotext", "-layout", pdf, "-"],
                           capture_output=True, timeout=60)
        return p.stdout.decode("utf-8", "replace")
    except Exception:
        return ""


def ocr_pdf(pdf: str, deadline: float, log=print):
    """OCR page by page, CACHING EACH PAGE. Returns (text, pages_done, complete).

    🔴 PER-PAGE CACHE, added 2026-08-01 after the first real run.
    Measured: ~7.5 s/page. A bash call is capped at 45 s (PLM-25), so a 30 s
    window does ~4 pages — and the first version threw them away and restarted
    the file from page 1 on the next call. An 8-page document would therefore
    NEVER have completed, no matter how many times it ran. It was "resumable"
    at file granularity in a world where no file fits in one window.
    Pages are now cached to disk, so every call makes permanent progress."""
    import hashlib
    key = hashlib.sha1(pdf.encode("utf-8")).hexdigest()[:16]
    cache = os.path.join(CACHE, key)
    os.makedirs(cache, exist_ok=True)
    tmp = tempfile.mkdtemp(prefix="ocr_")
    done = cached = 0
    complete = True
    out = []
    try:
        _, npages, _ = has_text_layer(pdf)
        npages = npages or 1
        for pg in range(1, npages + 1):
            cf = os.path.join(cache, "p%04d.txt" % pg)
            if os.path.exists(cf):
                out.append(open(cf, encoding="utf-8", errors="replace").read())
                cached += 1
                continue
            if time.time() > deadline:
                complete = False
                break
            stem = os.path.join(tmp, "p")
            try:
                subprocess.run(["pdftoppm", "-r", str(DPI), "-gray",
                                "-f", str(pg), "-l", str(pg), "-png", pdf, stem],
                               capture_output=True, timeout=40)
            except Exception:
                continue
            imgs = sorted(Path(tmp).glob("p-*.png"))
            if not imgs:
                continue
            try:
                r = subprocess.run(["tesseract", str(imgs[0]), "-", "--psm", "6"],
                                   capture_output=True, timeout=40)
                txt = "\n\n----- page %d -----\n%s" % (pg, r.stdout.decode("utf-8", "replace"))
                with open(cf, "w", encoding="utf-8") as fh:
                    fh.write(txt)
                out.append(txt)
                done += 1
            except Exception:
                pass
            for i in imgs:
                try:
                    i.unlink()
                except Exception:
                    pass
    finally:
        try:
            import shutil
            shutil.rmtree(tmp, ignore_errors=True)
        except Exception:
            pass
    if cached:
        log("      (%d page(s) from cache, %d new)" % (cached, done))
    return ("".join(out), done + cached, complete)


def candidates(under=""):
    base = os.path.join(ROOT, under) if under else ROOT
    hits = []
    for dp, _dn, fn in os.walk(base):
        for f in fn:
            if f.lower().endswith(".pdf"):
                hits.append(os.path.join(dp, f))
    hits.sort()
    return hits


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--under", default="")
    ap.add_argument("--seconds", type=float, default=35.0)
    ap.add_argument("--survey", action="store_true")
    ap.add_argument("--force", action="store_true")
    # --- RUN NATIVELY ON WINDOWS -------------------------------------------
    # Measured 2026-08-01: ~9 s/page on dense scanned email printouts. Against
    # the 45 s bash ceiling that is ~4 pages a call and ~95 calls for what is
    # left. Native Windows has no such ceiling, so the same job runs unattended
    # in one pass. These three flags are the only thing that was in the way.
    ap.add_argument("--root", default="")
    ap.add_argument("--out", default="")
    ap.add_argument("--cache", default="")
    a = ap.parse_args()

    global ROOT, OUT, CACHE, MANIFEST
    if a.root:
        ROOT = a.root.rstrip("\\/")
    if a.out:
        OUT = a.out.rstrip("\\/")
        MANIFEST = os.path.join(OUT, "_OCR_MANIFEST.jsonl")
    CACHE = a.cache or (os.path.join(OUT, "_ocr_cache") if a.out else CACHE)

    os.makedirs(OUT, exist_ok=True)
    os.makedirs(CACHE, exist_ok=True)
    if not os.path.isdir(ROOT):
        print("  [!] root not found: %s" % ROOT)
        return 1
    pdfs = candidates(a.under)

    if a.survey:
        need = ocr_pages = have = 0
        rows = []
        for p in pdfs:
            dst = os.path.join(OUT, flat_name(p))
            if os.path.exists(dst):
                have += 1
                continue
            n_ocr, n, per = has_text_layer(p)
            if n_ocr:
                need += 1
                ocr_pages += n
                rows.append((n, p))
            else:
                rows.append((0, p))
        rows.sort(reverse=True)
        print("  scope            : %s" % (a.under or "ALL of D:\\LEGAL"))
        print("  pdfs found       : %d" % len(pdfs))
        print("  already in corpus: %d" % have)
        print("  need OCR         : %d files / %d pages" % (need, ocr_pages))
        print("  text-layer only  : %d files (fast extract)" % sum(1 for n, _ in rows if n == 0))
        print("\n  --- outstanding, largest first ---")
        for n, p in rows[:12]:
            print("   %5s  %s" % (("%d pp" % n) if n else "text", os.path.relpath(p, ROOT)))
        return 0

    deadline = time.time() + a.seconds
    did = skipped = 0
    man = open(MANIFEST, "a", encoding="utf-8")
    for p in pdfs:
        if time.time() > deadline:
            break
        dst = os.path.join(OUT, flat_name(p))
        if os.path.exists(dst) and not a.force:
            skipped += 1
            continue
        needs, npages, per = has_text_layer(p)
        rel = os.path.relpath(p, ROOT)
        if not needs:
            txt = extract_text_layer(p)
            mode = "extract"
            complete = True
            pages = npages
        else:
            txt, pages, complete = ocr_pdf(p, deadline)
            mode = "ocr"
        if not txt.strip():
            print("   .. %-58s no text produced" % rel[:58])
            continue
        if not complete:
            # partial: do NOT write a truncated corpus file that looks whole
            print("   ~~ %-58s partial (%d/%d pp) - not written, will resume"
                  % (rel[:58], pages, npages))
            continue
        header = ("# %s\n# source: %s\n# mode: %s  pages: %d  ocr'd: %s\n\n"
                  % (os.path.basename(p), rel, mode, npages,
                     datetime.now().strftime("%Y-%m-%d")))
        with open(dst, "w", encoding="utf-8") as fh:
            fh.write(header + txt)
        man.write(json.dumps({"src": rel, "out": os.path.basename(dst), "mode": mode,
                              "pages": npages, "chars": len(txt),
                              "when": datetime.now().isoformat(timespec="seconds")}) + "\n")
        man.flush()
        did += 1
        print("   OK %-58s %s %3d pp %8d chars" % (rel[:58], mode, npages, len(txt)))
    man.close()
    print("  ---")
    print("  written this pass : %d" % did)
    print("  already present   : %d" % skipped)
    print("  re-run to continue (skip-if-exists makes it resumable)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
