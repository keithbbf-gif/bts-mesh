#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
bts_oagrab.py — OPEN-ACCESS PDF harvester for the dissertation library.

=============================================================================
  LEGAL RULE — NON-NEGOTIABLE, DO NOT "IMPROVE" THIS AWAY
=============================================================================
  This tool fetches ONLY legally open-access full text, from the publisher's
  or the author's own sanctioned surface: Crossref, Unpaywall, arXiv,
  Europe PMC / PMC.

  ABSOLUTELY FORBIDDEN:
    * Sci-Hub, LibGen, Z-Library, or ANY shadow library / mirror thereof.
    * Scraping content from behind a paywall.
    * Bypassing, spoofing or circumventing ANY access control, paywall,
      cookie wall, institutional proxy or login.

  Keith has ruled this out PERMANENTLY. If a paper is not legally free,
  this tool records it as NOT-AVAILABLE and moves on.
  *** THAT IS A SUCCESS, NOT A FAILURE. ***
  A NOT-AVAILABLE row is the correct, honest, complete answer. The paper can
  then be obtained through the university library / ILL, like a grown-up.

  BLOCKED_HOSTS below is a belt-and-braces check: even if some upstream API
  ever hands back a shadow-library URL, we refuse to fetch it.
=============================================================================

USAGE
  python bts_oagrab.py --doi 10.1038/s41598-023-40187-5
  python bts_oagrab.py --list wantlist.txt          # one DOI per line, # = comment
  python bts_oagrab.py --list wantlist.txt --outdir D:\tmp\staging --no-index
  python bts_oagrab.py --doi 10.xxxx/yyy --force    # re-fetch even if in library

BEHAVIOUR
  * Resolution ladder: Crossref (metadata + text-mining links) -> Unpaywall ->
    arXiv (title match) -> Europe PMC.
  * Saves to the house library with filename = THE PAPER TITLE, sanitised for
    Windows (existing house convention).
  * VERIFIES every download: first bytes must be %PDF and size must be > 20 KB.
    An HTML landing page or a "choose your institution" interstitial saved as
    .pdf is the classic silent failure. If it is not a real PDF we DELETE it
    and record NOT-AVAILABLE.
  * Resume-safe: a DOI already in the manifest, or whose title-file already
    exists in the library, is skipped.
  * Polite: >= 1.0 s between requests to the same host; identifies itself with
    a real mailto in the User-Agent (Crossref/Unpaywall "polite pool").
  * Appends results to 00_DOI_INDEX.md inside a marker-delimited section. It
    NEVER rewrites or clobbers anything else in that file.
"""

from __future__ import annotations

import argparse
import html
import json
import os
import re
import sys
import time
import unicodedata
import urllib.parse
from datetime import datetime, timezone

try:
    import requests
except ImportError:  # pragma: no cover
    sys.exit("bts_oagrab: needs `requests`  ->  pip install requests")

# ----------------------------------------------------------------------------
# config
# ----------------------------------------------------------------------------
EMAIL = "keith.bbf@gmail.com"
UA = f"bts_oagrab/1.0 (dissertation reference harvester; mailto:{EMAIL})"

LIB_DIR = r"V:\Research4\Ai\PhD2_DATA_ARCHIVE\papers\Grok_on_this\+Papers"
DOI_INDEX = r"V:\Research4\Ai\00_DOI_INDEX.md"
MANIFEST_NAME = "_oagrab_manifest.json"

MIN_PDF_BYTES = 20 * 1024          # anything smaller is not a paper
TIMEOUT = 45
MIN_HOST_GAP = 1.0                 # seconds between hits on the same host
MAX_REDIRECTS = 6

# see the legal rule at the top of this file. these are never fetched.
BLOCKED_HOSTS = (
    "sci-hub", "scihub", "libgen", "lib-gen", "gen.lib", "z-lib", "zlibrary",
    "b-ok", "booksc", "1lib", "pirate", "nexusstc", "annas-archive",
)

# markers for the section this tool owns inside 00_DOI_INDEX.md
IDX_BEGIN = "<!-- BEGIN bts_oagrab -->"
IDX_END = "<!-- END bts_oagrab -->"

_last_hit: dict[str, float] = {}


# ----------------------------------------------------------------------------
# plumbing
# ----------------------------------------------------------------------------
def log(msg: str) -> None:
    # 2026-07-14: this CRASHED THE WHOLE HARVEST at DOI 7/33 —
    #   UnicodeEncodeError: 'charmap' codec can't encode character '‐'
    # A Crossref title carried a U+2010 HYPHEN; piping to a file on Windows gives stdout the cp1252
    # codepage, which has no such character. A run that dies two-thirds of the way through a wantlist
    # (and exits 1 AFTER writing some PDFs) is a nasty failure: it looks like a network problem and it
    # silently loses the tail of the list. Never let a PRINT kill a HARVEST.
    try:
        print(msg, flush=True)
    except UnicodeEncodeError:
        enc = (getattr(sys.stdout, "encoding", None) or "ascii")
        print(msg.encode(enc, "replace").decode(enc, "replace"), flush=True)


def _host(url: str) -> str:
    try:
        return (urllib.parse.urlsplit(url).hostname or "").lower()
    except ValueError:
        return ""


def is_blocked(url: str) -> bool:
    """Refuse shadow libraries outright, wherever the URL came from."""
    h = _host(url)
    return any(bad in h for bad in BLOCKED_HOSTS)


def polite(url: str) -> None:
    """>= MIN_HOST_GAP seconds between requests to the same host."""
    h = _host(url)
    now = time.time()
    prev = _last_hit.get(h)
    if prev is not None:
        wait = MIN_HOST_GAP - (now - prev)
        if wait > 0:
            time.sleep(wait)
    _last_hit[h] = time.time()


def get(url: str, **kw):
    if is_blocked(url):
        raise PermissionError(f"BLOCKED (shadow library / forbidden host): {url}")
    polite(url)
    kw.setdefault("timeout", TIMEOUT)
    kw.setdefault("headers", {}).setdefault("User-Agent", UA)
    return requests.get(url, **kw)


# ----------------------------------------------------------------------------
# filename handling — the house convention is: filename = PAPER TITLE
# ----------------------------------------------------------------------------
_TAG = re.compile(r"<[^>]+>")
_WS = re.compile(r"\s+")
_ILLEGAL = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def clean_title(raw: str) -> str:
    """Crossref titles carry JATS/MathML tags and HTML entities. Strip them."""
    t = _TAG.sub("", raw or "")
    t = html.unescape(t)
    t = unicodedata.normalize("NFC", t)
    return _WS.sub(" ", t).strip()


def safe_filename(title: str, limit: int = 150) -> str:
    """
    Windows-safe. Matches what is already on disk in the library:
      ':' and '/' become ' - ' / '-'  (e.g. "Ultraviolet photoelectron
      spectroscopy - Practical aspects and best practices"), brackets kept.
    """
    t = title.replace(":", " -").replace("/", "-")
    t = _ILLEGAL.sub("", t)
    t = _WS.sub(" ", t).strip().rstrip(". ")
    if len(t) > limit:
        t = t[:limit].rsplit(" ", 1)[0].rstrip(". ,;-")
    return t or "untitled"


def norm_for_match(s: str) -> str:
    """Aggressive normalisation, for comparing an arXiv title to a Crossref one."""
    s = unicodedata.normalize("NFKD", clean_title(s).lower())
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", "", s)


# ----------------------------------------------------------------------------
# manifest (resume safety)
# ----------------------------------------------------------------------------
def manifest_path(outdir: str) -> str:
    return os.path.join(outdir, MANIFEST_NAME)


def load_manifest(outdir: str) -> dict:
    p = manifest_path(outdir)
    if not os.path.isfile(p):
        return {}
    try:
        with open(p, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        log(f"  ! manifest unreadable, starting a fresh one: {p}")
        return {}


def save_manifest(outdir: str, man: dict) -> None:
    tmp = manifest_path(outdir) + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(man, fh, indent=1, ensure_ascii=False, sort_keys=True)
    os.replace(tmp, manifest_path(outdir))


def already_have(doi: str, title: str | None, outdir: str, man: dict) -> str | None:
    """Return the existing filename if this DOI/title is already in the library."""
    rec = man.get(doi.lower())
    if rec and rec.get("file"):
        if os.path.isfile(os.path.join(outdir, rec["file"])):
            return rec["file"]
    if title:
        fn = safe_filename(title) + ".pdf"
        if os.path.isfile(os.path.join(outdir, fn)):
            return fn
    return None


# ----------------------------------------------------------------------------
# the one function that stops us lying to ourselves
# ----------------------------------------------------------------------------
def looks_like_pdf(blob: bytes) -> bool:
    """A real PDF starts with %PDF (some servers prepend a little junk)."""
    return b"%PDF" in blob[:1024]


def try_pdf(url: str, dest: str, referer: str | None = None) -> tuple[bool, int, str]:
    """
    Download `url` to `dest`, then PROVE it is a PDF.
    Returns (ok, nbytes, note). On failure the partial file is DELETED.
    """
    if is_blocked(url):
        return (False, 0, "blocked host (shadow library) — refused")
    hdrs = {"User-Agent": UA, "Accept": "application/pdf,*/*"}
    if referer:
        hdrs["Referer"] = referer
    try:
        r = get(url, headers=hdrs, allow_redirects=True, stream=True)
    except PermissionError as exc:
        return (False, 0, str(exc))
    except requests.RequestException as exc:
        return (False, 0, f"network error: {type(exc).__name__}")

    if is_blocked(r.url):  # a redirect could land somewhere forbidden
        r.close()
        return (False, 0, "redirected to a blocked host — refused")
    if r.status_code != 200:
        r.close()
        return (False, 0, f"HTTP {r.status_code}")

    ctype = (r.headers.get("Content-Type") or "").split(";")[0].strip().lower()

    try:
        with open(dest, "wb") as fh:
            n = 0
            head = b""
            for chunk in r.iter_content(65536):
                if not chunk:
                    continue
                if not head:
                    head = chunk[:1024]
                fh.write(chunk)
                n += len(chunk)
    except (OSError, requests.RequestException) as exc:
        _unlink(dest)
        return (False, 0, f"write/stream error: {type(exc).__name__}")
    finally:
        r.close()

    # --- the two verifications. a landing page is NOT a paper. ---
    if not looks_like_pdf(head):
        _unlink(dest)
        sniff = "HTML" if b"<html" in head.lower() or ctype == "text/html" else (ctype or "?")
        return (False, n, f"NOT a PDF (got {sniff}, {n} B) — deleted")
    if n < MIN_PDF_BYTES:
        _unlink(dest)
        return (False, n, f"PDF too small ({n} B < {MIN_PDF_BYTES}) — deleted")
    return (True, n, ctype or "application/pdf")


def _unlink(p: str) -> None:
    try:
        os.remove(p)
    except OSError:
        pass


# ----------------------------------------------------------------------------
# source 1 — Crossref (metadata + text-mining links)
# ----------------------------------------------------------------------------
def crossref(doi: str) -> dict | None:
    url = f"https://api.crossref.org/works/{urllib.parse.quote(doi)}?mailto={EMAIL}"
    try:
        r = get(url)
    except requests.RequestException as exc:
        log(f"  crossref: network error ({type(exc).__name__})")
        return None
    if r.status_code == 404:
        log("  crossref: 404 — DOI DOES NOT EXIST")
        return None
    if r.status_code != 200:
        log(f"  crossref: HTTP {r.status_code}")
        return None
    try:
        m = r.json()["message"]
    except (ValueError, KeyError):
        log("  crossref: unparseable response")
        return None

    title = clean_title((m.get("title") or [""])[0])
    authors = []
    for a in (m.get("author") or [])[:12]:
        nm = " ".join(x for x in (a.get("given"), a.get("family")) if x)
        if nm:
            authors.append(nm)
    date = (m.get("issued", {}).get("date-parts") or [[None]])[0]
    year = date[0] if date and date[0] else None

    pdf_links = []
    for lk in m.get("link") or []:
        if (lk.get("content-type") or "").lower() == "application/pdf":
            app = (lk.get("intended-application") or "").lower()
            if app in ("text-mining", "similarity-checking") and lk.get("URL"):
                pdf_links.append(lk["URL"])

    return {
        "doi": doi,
        "title": title,
        "authors": authors,
        "year": year,
        "journal": clean_title((m.get("container-title") or [""])[0]),
        "type": m.get("type", ""),
        "pdf_links": pdf_links,
    }


# ----------------------------------------------------------------------------
# source 2 — Unpaywall (THE tool for this job)
# ----------------------------------------------------------------------------
def unpaywall(doi: str) -> list[str]:
    url = f"https://api.unpaywall.org/v2/{urllib.parse.quote(doi)}?email={EMAIL}"
    try:
        r = get(url)
    except requests.RequestException as exc:
        log(f"  unpaywall: network error ({type(exc).__name__})")
        return []
    if r.status_code == 404:
        log("  unpaywall: 404 — not in Unpaywall")
        return []
    if r.status_code != 200:
        log(f"  unpaywall: HTTP {r.status_code}")
        return []
    try:
        d = r.json()
    except ValueError:
        return []

    if not d.get("is_oa"):
        log(f"  unpaywall: is_oa = False  (journal_is_oa={d.get('journal_is_oa')})")
        return []

    urls: list[str] = []
    best = d.get("best_oa_location") or {}
    if best.get("url_for_pdf"):
        urls.append(best["url_for_pdf"])
    for loc in d.get("oa_locations") or []:
        u = loc.get("url_for_pdf")
        if u and u not in urls:
            urls.append(u)
    log(f"  unpaywall: is_oa = True, {len(urls)} pdf url(s), status={d.get('oa_status')}")
    return [u for u in urls if not is_blocked(u)]


# ----------------------------------------------------------------------------
# source 3 — arXiv (match on title; arXiv PDFs are always free)
# ----------------------------------------------------------------------------
def arxiv(title: str) -> list[str]:
    if not title:
        return []
    # quote the title so the arXiv API treats it as a phrase
    q = 'ti:"%s"' % re.sub(r'["\\]', " ", title)
    url = ("http://export.arxiv.org/api/query?search_query="
           + urllib.parse.quote(q, safe=":\"")
           + "&start=0&max_results=5")
    try:
        r = get(url)
    except requests.RequestException as exc:
        log(f"  arxiv: network error ({type(exc).__name__})")
        return []
    if r.status_code != 200:
        log(f"  arxiv: HTTP {r.status_code}")
        return []

    want = norm_for_match(title)
    hits: list[str] = []
    # the Atom feed is small and regular; no XML dep needed
    for entry in re.findall(r"<entry>(.*?)</entry>", r.text, re.S):
        tm = re.search(r"<title>(.*?)</title>", entry, re.S)
        im = re.search(r"<id>(.*?)</id>", entry, re.S)
        if not tm or not im:
            continue
        got = norm_for_match(tm.group(1))
        if not got or not want:
            continue
        # require a genuine title match, not just "arXiv returned something"
        if got != want and want not in got and got not in want:
            continue
        aid = im.group(1).strip().rsplit("/abs/", 1)[-1]
        hits.append(f"https://arxiv.org/pdf/{aid}")
    log(f"  arxiv: {len(hits)} title-matched hit(s)")
    return hits


# ----------------------------------------------------------------------------
# source 4 — Europe PMC / PMC
# ----------------------------------------------------------------------------
def europepmc(doi: str) -> list[str]:
    url = ("https://www.ebi.ac.uk/europepmc/webservices/rest/search"
           f"?query=DOI:%22{urllib.parse.quote(doi)}%22&format=json&pageSize=5")
    try:
        r = get(url)
    except requests.RequestException as exc:
        log(f"  europepmc: network error ({type(exc).__name__})")
        return []
    if r.status_code != 200:
        log(f"  europepmc: HTTP {r.status_code}")
        return []
    try:
        results = r.json().get("resultList", {}).get("result", []) or []
    except ValueError:
        return []

    urls: list[str] = []
    for res in results:
        pmcid = res.get("pmcid")
        if not pmcid:
            continue
        if (res.get("isOpenAccess") or "").upper() != "Y":
            log(f"  europepmc: {pmcid} present but isOpenAccess != Y")
            continue
        urls.append(f"https://europepmc.org/articles/{pmcid}?pdf=render")
    log(f"  europepmc: {len(urls)} OA pmcid(s)")
    return urls


# ----------------------------------------------------------------------------
# the ladder
# ----------------------------------------------------------------------------
def harvest(doi: str, outdir: str, man: dict, force: bool = False) -> dict:
    doi = doi.strip().rstrip(".,;")
    doi = re.sub(r"^(https?://(dx\.)?doi\.org/|doi:\s*)", "", doi, flags=re.I).strip()
    row = {"doi": doi, "title": "", "source": "-", "bytes": 0,
           "status": "NOT-AVAILABLE", "file": "", "note": ""}
    log(f"\n=== {doi}")

    # ---- 1. Crossref: authoritative metadata --------------------------------
    meta = crossref(doi)
    if not meta:
        row["note"] = "DOI not found in Crossref (does not exist / not registered)"
        log(f"  -> NOT-AVAILABLE ({row['note']})")
        return row

    row["title"] = meta["title"]
    first = meta["authors"][0].split()[-1] if meta["authors"] else "?"
    log(f"  title : {meta['title'][:96]}")
    log(f"  meta  : {first} et al., {meta['journal']}, {meta['year']}")

    if not force:
        have = already_have(doi, meta["title"], outdir, man)
        if have:
            row.update(status="SKIP", source="library", file=have,
                       bytes=os.path.getsize(os.path.join(outdir, have)),
                       note="already in library")
            log(f"  -> SKIP (already in library: {have})")
            return row

    dest = os.path.join(outdir, safe_filename(meta["title"]) + ".pdf")

    # candidate URLs, in the mandated order
    cands: list[tuple[str, str]] = []
    cands += [("crossref", u) for u in meta["pdf_links"]]           # text-mining links
    cands += [("unpaywall", u) for u in unpaywall(doi)]
    cands += [("arxiv", u) for u in arxiv(meta["title"])]
    cands += [("pmc", u) for u in europepmc(doi)]

    if not cands:
        row["note"] = "no OA full-text location found (paywalled)"
        log(f"  -> NOT-AVAILABLE ({row['note']})")
        return row

    seen: set[str] = set()
    for src, url in cands:
        if url in seen:
            continue
        seen.add(url)
        log(f"  try [{src}] {url[:110]}")
        ok, n, note = try_pdf(url, dest, referer=f"https://doi.org/{doi}")
        if ok:
            row.update(status="OK", source=src, bytes=n,
                       file=os.path.basename(dest), note=note)
            log(f"  -> OK  {n:,} B via {src}  ->  {os.path.basename(dest)}")
            man[doi.lower()] = {
                "file": os.path.basename(dest), "title": meta["title"],
                "source": src, "url": url, "bytes": n, "year": meta["year"],
                "journal": meta["journal"],
                "fetched": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            }
            return row
        log(f"     x {note}")
        row["note"] = note

    row["note"] = "all OA candidates failed verification (%PDF / >20 KB)"
    log(f"  -> NOT-AVAILABLE ({row['note']})")
    return row


# ----------------------------------------------------------------------------
# 00_DOI_INDEX.md — append only, inside our own markers. never clobber.
# ----------------------------------------------------------------------------
def update_doi_index(rows: list[dict], index_path: str = DOI_INDEX) -> None:
    """
    APPEND-ONLY. This function opens the index in "a" mode and NEVER reads it,
    never rewrites it, never os.replace()s it.

    WHY (scar tissue, 2026-07-13): the first version did a read-modify-write.
    Run through a FUSE mount of D:, the READ came back silently TRUNCATED, and
    the tool then wrote that truncated copy back — destroying section 4 of
    00_DOI_INDEX.md. The file was fine on disk; the read was the liar. See the
    "sandbox reads are NOT evidence" rule in CLAUDE.md.
    Append-only makes that failure mode impossible: a corrupt read cannot
    clobber what we never read.
    """
    if not os.path.isfile(index_path):
        log(f"  ! DOI index not found, not creating one: {index_path}")
        return

    stamp = datetime.now().strftime("%Y-%m-%d")
    lines = []
    for r in rows:
        oa = {"OK": "**OA**", "SKIP": "have", "NOT-AVAILABLE": "no"}[r["status"]]
        cite = r["title"][:88] or "(unresolved)"
        got = (f"`{r['file']}` ({r['bytes']:,} B, {r['source']})"
               if r["status"] == "OK" else
               f"already in library — `{r['file']}`" if r["status"] == "SKIP"
               else f"**NOT AVAILABLE** — {r['note']}")
        lines.append(f"| {stamp} | {cite} | `{r['doi']}` | {oa} | {got} |")

    size_before = os.path.getsize(index_path)

    # Same pipe-table style as the rest of the file. Each run appends a
    # self-contained block with its own header row, so the block is valid
    # markdown on its own and no earlier byte is ever touched.
    block = (
        f"\n{IDX_BEGIN} {stamp}\n\n"
        f"### OA harvest — {stamp} (`Ai\\BTS_MESH\\bts_oagrab.py`)\n\n"
        "**NOT AVAILABLE = the paper is not legally free.** No shadow libraries, ever —\n"
        "those go through the LSU library / ILL.\n\n"
        "| run | citation | DOI | OA | result |\n"
        "|---|---|---|---|---|\n"
        + "\n".join(lines) + "\n"
        + f"{IDX_END}\n"
    )
    with open(index_path, "a", encoding="utf-8") as fh:
        fh.write(block)

    size_after = os.path.getsize(index_path)
    if size_after < size_before:  # can only happen if something is very wrong
        log(f"  !! INDEX SHRANK ({size_before} -> {size_after} B). "
            f"Restore it from git/backup. THIS IS A BUG — report it.")
    else:
        log(f"  index appended: {index_path} "
            f"(+{len(lines)} row(s), {size_before} -> {size_after} B)")


# ----------------------------------------------------------------------------
# main
# ----------------------------------------------------------------------------
def main() -> int:
    ap = argparse.ArgumentParser(
        description="Harvest LEGALLY open-access PDFs by DOI. No shadow libraries. Ever.")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--doi", help="a single DOI")
    g.add_argument("--list", dest="listfile", help="file of DOIs, one per line (# = comment)")
    ap.add_argument("--outdir", default=LIB_DIR, help=f"library dir (default: {LIB_DIR})")
    ap.add_argument("--index", default=DOI_INDEX, help="00_DOI_INDEX.md to append to")
    ap.add_argument("--no-index", action="store_true", help="do not touch 00_DOI_INDEX.md")
    ap.add_argument("--force", action="store_true", help="re-fetch even if already in library")
    args = ap.parse_args()

    if args.doi:
        dois = [args.doi]
    else:
        with open(args.listfile, "r", encoding="utf-8-sig") as fh:
            dois = [ln.strip() for ln in fh
                    if ln.strip() and not ln.lstrip().startswith("#")]

    os.makedirs(args.outdir, exist_ok=True)
    man = load_manifest(args.outdir)

    log(f"bts_oagrab — {len(dois)} DOI(s) -> {args.outdir}")
    log("legal sources only: crossref / unpaywall / arxiv / europepmc. "
        "no shadow libraries.")

    rows = [harvest(d, args.outdir, man, force=args.force) for d in dois]
    save_manifest(args.outdir, man)

    # ---- run log -----------------------------------------------------------
    log("\n" + "=" * 100)
    log("RUN LOG")
    log("=" * 100)
    log(f"{'DOI':<32} {'SOURCE':<10} {'BYTES':>10}  {'STATUS':<14} TITLE")
    log("-" * 100)
    for r in rows:
        log(f"{r['doi']:<32} {r['source']:<10} {r['bytes']:>10,}  {r['status']:<14} "
            f"{(r['title'] or r['note'])[:44]}")
    ok = sum(r["status"] == "OK" for r in rows)
    sk = sum(r["status"] == "SKIP" for r in rows)
    na = sum(r["status"] == "NOT-AVAILABLE" for r in rows)
    log("-" * 100)
    log(f"{ok} downloaded and VERIFIED (%PDF, >{MIN_PDF_BYTES // 1024} KB) | "
        f"{sk} already had | {na} NOT AVAILABLE (not legally free — this is fine)")

    if not args.no_index:
        update_doi_index(rows, args.index)

    return 0


if __name__ == "__main__":
    sys.exit(main())
