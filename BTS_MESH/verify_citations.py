#!/usr/bin/env python3
"""verify_citations.py — THREE-LINEAGE CITATION CHECK.  2026-07-30

    "The real test is not verification by another agent or AI. It's three independent searches
     that return the SAME citations."  — Keith, 2026-07-30

So this file contains **no model call of any kind**. It resolves every DOI against three registries
with different lineages and reports where they agree. It is a program, not a prompt: deterministic,
free, sub-second per lookup, and repeatable by a sceptic who does not trust us.

ADOPTED, NOT INVENTED (RULE R14 — survey before you build, 2026-07-30)
---------------------------------------------------------------------
The pattern here is the one every working tool converges on: extract -> resolve against several
independent registries -> report per citation. Prior art surveyed and named, so this decision is
falsifiable rather than a habit:
  * kazilab/xRef      open source; six registries from one HTML app. Browser-driven, so unsuitable
                      for an unattended gate, but it is the reference design and this follows it.
  * Cite Checker      open source; Crossref + OpenAlex over ~200M records.
  * CiteMe / Citely   hosted; CiteMe publishes 88.7% correct / 2.4% false positive on 369 refs.
WHY WE STILL HAVE A LOCAL SCRIPT: we need an UNATTENDED GATE that runs in TidyUP, writes an
append-only record, and fails loudly. None of the above is a library we can call from a scheduled
task. We adopt their registries and their matching pattern; we do not reimplement their matching.

THE THREE LINEAGES
------------------
  1. CROSSREF        api.crossref.org      THE AUTHORITY — the registration agency itself.
  2. OPENALEX        api.openalex.org      independent index, own harvesting pipeline.
  3. SEMANTIC SCHOLAR api.semanticscholar.org  independent corpus (AI2).

VERDICTS
  PASS      the authority resolves AND at least one independent index agrees on the title.
  WEAK      the authority resolves, but no independent index has it. Real but unreplicated —
            common for pre-2000 and conference DOIs. NOT a failure; it is a flag for a human.
  FAIL      the authority does not resolve. The citation does not exist. Do not ship it.
  TITLEDIFF registries disagree about what the DOI IS. Rarer and more serious than a 404.

⚠ INDEPENDENCE IS OF LINEAGE, NOT OF QUERY. OpenAlex and Semantic Scholar both ingest Crossref
metadata, so agreement between them is weaker evidence than it looks. That is why the authority is
required and never merely counted as "one of three". Recorded here so nobody later mistakes three
HTTP calls for three witnesses.

NEGATIVE CONTROL — a check never shown to fail is not a check (RULES.md):
    python verify_citations.py --selftest
asserts an unregistered DOI comes back FAIL and two real ones come back PASS — and deliberately
includes the Au 5d DOI, which PASSES because it is REAL AND MISATTRIBUTED (see SCARS S-91). That
third line is the instrument's own limit, kept in the test so nobody forgets it: **existence is not
support, and no registry check anywhere can close that gap.**

⚠ RUN THIS NATIVELY ON WINDOWS. Proven 2026-07-30: the Linux sandbox mount read
`Ai\00_DOI_INDEX.md` and returned **0 DOIs** where a host-side grep returns **78**. The network is
fine from the sandbox; the FILE READ is not. Reading the citation list through the mount would
silently verify an empty set and report success.
"""
from __future__ import annotations

import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor

UA = "BFast-verify_citations/1.0 (mailto:keith.bbf@gmail.com)"
DOI_RE = re.compile(r"10\.\d{4,9}/[^\s)\]\"'`,]+")
TIMEOUT = 12


def _get(url: str, retries: int = 2):
    """Return (status, json). status None = UNREACHABLE, which is NOT the same as 404.

    🔴 FIXED 2026-07-30, on the first real run. The first version collapsed 'timed out' and
    'does not exist' into the same False, and duly reported two perfectly real DOIs as FAIL —
    with the tell visible in its own output (the independent indices had them). **A test that
    cannot distinguish "no" from "no answer" does not discriminate, and a test that does not
    discriminate has not been run.** Anything unreachable is NOT MEASURED, never inferred.
    """
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
                return r.status, json.loads(r.read().decode("utf-8", "replace"))
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503, 504) and attempt < retries:
                time.sleep(1.5 * (attempt + 1))
                continue
            return e.code, None                      # a real 404 lands here
        except Exception:
            if attempt < retries:
                time.sleep(1.0 * (attempt + 1))
                continue
            return None, None                        # unreachable — NOT MEASURED


def _norm(t) -> str:
    """Crossref embeds MathML in titles (`<mml:math ...>`), which shreds any token comparison and
    produced a false TITLEDIFF on PhysRevLett.66.1741 on the first run. Strip markup first."""
    if isinstance(t, list):
        t = t[0] if t else ""
    t = re.sub(r"<[^>]+>", " ", str(t or ""))
    t = re.sub(r"\b(mml|math|xmlns|http|www|w3|org|1998|mathml|mrow|mi|mo|mn|msub|msup)\b", " ",
               t, flags=re.I)
    return re.sub(r"[^a-z0-9]+", " ", t.lower()).strip()


def _similar(a: str, b: str) -> float:
    """Token overlap. Deliberately crude: we are detecting 'this DOI is a different paper',
    not grading bibliographic style."""
    A, B = set(_norm(a).split()), set(_norm(b).split())
    if not A or not B:
        return 0.0
    return len(A & B) / max(len(A), len(B))


def crossref(doi):
    """Returns (state, title). state: True=registered · False=404, definitively not registered ·
    None=UNREACHABLE, which must never be reported as a missing citation."""
    st, d = _get("https://api.crossref.org/works/" + urllib.parse.quote(doi))
    if st == 200 and d:
        return True, _norm((d.get("message") or {}).get("title"))
    if st == 404:
        return False, ""
    return None, ""


def openalex(doi):
    st, d = _get("https://api.openalex.org/works/doi:" + urllib.parse.quote(doi))
    if st == 200 and d:
        return True, _norm(d.get("title") or d.get("display_name"))
    return False, ""


def semanticscholar(doi):
    st, d = _get("https://api.semanticscholar.org/graph/v1/paper/DOI:"
                 + urllib.parse.quote(doi) + "?fields=title")
    if st == 200 and d:
        return True, _norm(d.get("title"))
    return False, ""


LINEAGES = [("CROSSREF", crossref), ("OPENALEX", openalex), ("S2", semanticscholar)]


def check(doi: str) -> dict:
    doi = doi.rstrip(".,;)*").strip()
    hits = {}
    for name, fn in LINEAGES:
        ok, title = fn(doi)
        hits[name] = (ok, title)

    auth_ok, auth_title = hits["CROSSREF"]
    others = [(n, t) for n, (ok, t) in hits.items() if ok and n != "CROSSREF"]

    if auth_ok is None:
        return {"doi": doi, "verdict": "NOTMEAS", "n": len(others),
                "detail": "the AUTHORITY was unreachable — not a missing citation, an unrun test"}
    if not auth_ok:
        found_elsewhere = [n for n, _ in others]
        return {"doi": doi, "verdict": "FAIL", "n": len(others),
                "detail": ("authority (Crossref) does not resolve it"
                           + (f" — but {'/'.join(found_elsewhere)} claims it exists, which is "
                              "CIRCULATION, not registration" if found_elsewhere else ""))}
    if not others:
        return {"doi": doi, "verdict": "WEAK", "n": 1,
                "detail": "registered, but no independent index replicates it — human check"}
    worst = min(_similar(auth_title, t) for _, t in others)
    if worst < 0.34:
        return {"doi": doi, "verdict": "TITLEDIFF", "n": 1 + len(others),
                "detail": f"registries disagree on the title (overlap {worst:.2f}): "
                          f"{auth_title[:60]!r}"}
    return {"doi": doi, "verdict": "PASS", "n": 1 + len(others),
            "detail": f"{1 + len(others)} lineages agree · {auth_title[:70]}"}


def run(dois, workers: int = 12) -> int:
    dois = sorted({d.rstrip(".,;)*").strip() for d in dois if d})
    with ThreadPoolExecutor(max_workers=workers) as ex:
        results = list(ex.map(check, dois))
    order = {"FAIL": 0, "TITLEDIFF": 1, "NOTMEAS": 2, "WEAK": 3, "PASS": 4}
    results.sort(key=lambda r: (order[r["verdict"]], r["doi"]))
    print("=" * 100)
    print("  verify_citations  |  three lineages: CROSSREF (authority) + OPENALEX + SEMANTIC SCHOLAR")
    print("=" * 100)
    for r in results:
        if r["verdict"] != "PASS":
            print(f"  {r['verdict']:<10} {r['doi']:<42} {r['detail']}")
    counts = {k: sum(1 for r in results if r["verdict"] == k) for k in order}
    print("-" * 100)
    print(f"  checked={len(results)}  PASS={counts['PASS']}  WEAK={counts['WEAK']}  "
          f"TITLEDIFF={counts['TITLEDIFF']}  NOT-MEASURED={counts['NOTMEAS']}  FAIL={counts['FAIL']}")
    print(f"  RESULT: {'RED — a citation does not exist' if counts['FAIL'] else 'GREEN'}")
    return counts["FAIL"]


def from_file(path: str) -> list:
    with open(path, encoding="utf-8", errors="replace") as fh:
        text = fh.read()
    found = DOI_RE.findall(text)
    if not found:
        print(f"  *** NO DOIs FOUND IN {path} ***")
        print("  Refusing to report success on an empty set. If you are on Linux this is almost")
        print("  certainly the mount: it returned 0 DOIs for a file a host-side grep reads as 78.")
        sys.exit(2)
    return found


def selftest() -> int:
    """NEGATIVE CONTROL — and a standing demonstration of this instrument's LIMIT.

    🔴 THE LIMIT, MEASURED ON ITS FIRST RUN, 2026-07-30. This selftest was written asserting that
    `10.1002/adma.201906478` would FAIL, because this project's own record calls it a FABRICATED
    citation returned by a node for the Au 5d falling-edge claim. **It does not fail. It resolves in
    all three lineages** as "A Noble Transition Alloy Excels at Hot Carrier Generation in the Near
    Infrared" — a real Advanced Materials paper about something else entirely.

    So the DOI was never fabricated. It was **MISATTRIBUTED**: a genuine identifier attached to a
    claim it does not support. That is a worse failure than invention, because **every existence
    check in the world passes it** — including this one, including all three lineages, including the
    commercial tools. Only reading the source catches it.

    ⇒ This test now asserts that behaviour deliberately, so the limit can never be forgotten:
       a real-but-wrong citation MUST come back PASS here, and the standard must therefore never
       claim that a green existence check means a citation supports its claim.
    """
    print("--- selftest: existence check. One unregistered DOI must FAIL; two real ones must PASS ---")
    fake = "10.1002/adma.209999999"      # valid prefix, never registered
    good = "10.1103/PhysRevB.13.492"     # Lindau/Pianetta/Yu/Spicer 1976 — in our library
    mis = "10.1002/adma.201906478"       # REAL paper, WRONG claim. See the docstring above.
    r1, r2, r3 = check(fake), check(good), check(mis)
    for r in (r1, r2, r3):
        print(f"  {r['verdict']:<10} {r['doi']:<42} {r['detail']}")
    ok = r1["verdict"] == "FAIL" and r2["verdict"] == "PASS" and r3["verdict"] == "PASS"
    print()
    print("  NOTE: the third line is a MISATTRIBUTED citation and it PASSES, correctly.")
    print("        Existence is not support. Only reading the source closes that gap.")
    print("SELFTEST PASS — RED on an unregistered DOI, GREEN on real ones, and the known"
          " misattribution passes exactly as it must." if ok else
          "SELFTEST FAIL — this check cannot be trusted.")
    return 0 if ok else 1


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(selftest())
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    if not args:
        print(__doc__)
        sys.exit(2)
    sys.exit(1 if run(from_file(args[0])) else 0)
