#!/usr/bin/env python3
"""
rfa_review.py - put the seven proposed requests for admission to another family for critique.

Keith, 2026-08-03: "We need a way to cross-check you. I cannot, I don't have the knowledge."

WHY THIS EXISTS AND WHY IT IS NOT THE WAR GAME
  wargame_feed.py builds a NEUTRAL record and asks a model to argue a side. Nothing of Cowork's
  analysis is allowed into it, because the point there is to see what an independent reader makes
  of the documents.

  This is the opposite. The point here is to attack COWORK'S OWN WORK PRODUCT, so the work product
  is the subject and must be included. The tasking says plainly that a review approving everything
  is useless.

  ⇒ Two tools, two neutrality rules. Do not confuse them, and do not "fix" this one by stripping
    the proposal out of it.

WHAT IT SENDS
  The EXPANDED record - the trial record plus bundle 09_JASPER_UCC, which the war game excluded
  because those documents are not in evidence. For this purpose they are exactly what is needed:
  five of the seven proposed requests concern the alleged transfer to Abraxas Scientific and Jasper.

  Build it first:  py -3.14 wargame_feed.py --build --expanded

USAGE (native Windows - the sandbox cannot write the ledger across the mount)
    py -3.14 rfa_review.py --node sgh
    py -3.14 rfa_review.py --selftest
"""
from __future__ import annotations
import argparse, json, re, sys, time
from datetime import datetime
from pathlib import Path

MESH = Path(__file__).resolve().parent
sys.path.insert(0, str(MESH))

WG      = Path(r"V:\Ai\Legal\WARGAME")
RECORD  = WG / "record"
OUT     = Path(r"V:\Ai\Legal\RFA_REVIEW")
TASKING = OUT / "REVIEW_TASKING.txt"
LEDGER  = WG / "_LEDGER.jsonl"
BUNDLE  = re.compile(r'^\d{2}_[A-Z_]+__')

# Same measured ceilings as fire_one_rail. grok-build is not here: 256K cannot hold the record.
CTX = {"gem": ("gemini-2.5-pro", 1_000_000),
       "sgh": ("grok-4.5",         500_000),
       "g43": ("grok-4.3",       1_000_000)}


# ---------------------------------------------------------------------------------------------
# THE ONLY DOCUMENT THIS TOOL MAY DROP TO FIT A WINDOW.
#
# The expanded record estimates ~514K tokens and SGH holds 500K. The temptation is a per-document
# character cap, and that is the WRONG fix here: a uniform cap bites the SOP file and the
# production PDF, which are precisely the documents requests 27 and 30 turn on. Truncating the
# middle of the evidence to make room is how a review comes back confidently wrong.
#
# So: drop ONE named document instead, and only when the window forces it. The Agilent maintenance
# manual is vendor boilerplate. wargame_feed.py already excludes its two siblings by the reason
# "[VENDOR MANUAL - pump]"; this one is the autosampler/main manual and slipped the filter. It
# bears on nothing in a critique of requests for admission.
FIT_DROP = {"06_INSTRUMENT__Abraxas Case__Abraxas Discovery Reply__hplc1100-maintenance.pdf.txt":
            "vendor maintenance manual - its two siblings are already excluded by the feed"}


def load_record(drop: set[str] | None = None) -> tuple[str, int]:
    """Whitelist by bundle prefix, same rule as the war game - a stray memo cannot wander in."""
    drop = drop or set()
    docs = sorted(p for p in RECORD.glob("*.txt")
                  if BUNDLE.match(p.name) and p.name not in drop)
    if not docs:
        raise SystemExit(f"no record at {RECORD} - build it: wargame_feed.py --build --expanded")
    rejected = [p.name for p in RECORD.glob("*.txt") if not BUNDLE.match(p.name)]
    if rejected:
        print(f"  whitelist kept OUT: {', '.join(sorted(rejected))}")

    # A rebuild does not clear this directory, so a document from an EARLIER build survives it and
    # would be fed silently. Say so. Do not auto-remove - the 02_DISCOVERY responses file was
    # hand-placed and is wanted.
    if len(docs) > 1:
        newest = max(p.stat().st_mtime for p in docs)
        stale = [p.name for p in docs if newest - p.stat().st_mtime > 6 * 3600]
        if stale:
            print(f"  ⚠ {len(stale)} document(s) predate this build by >6h - survivors of an")
            print(f"    earlier build, not written by it. Confirm they belong:")
            for n in sorted(stale):
                print(f"      {n}")

    parts = []
    for p in docs:
        declared = p.stat().st_size
        raw = p.read_bytes()
        if len(raw) != declared:                       # the mount has lied 13 times
            raise SystemExit(f"TRUNCATED READ on {p.name}: {len(raw)} vs {declared} - aborting")
        parts.append("\n\n===== DOCUMENT: " + p.name + " =====\n"
                     + raw.decode("utf-8", "replace"))
    return "".join(parts), len(docs)


def has_jasper() -> bool:
    return any(p.name.startswith("09_") for p in RECORD.glob("*.txt"))


def fire(node: str, no_fit: bool = False) -> int:
    if not TASKING.exists():
        raise SystemExit(f"no tasking at {TASKING}")
    rec, n = load_record()
    prompt = TASKING.read_text(encoding="utf-8") + rec
    model, ctx = CTX[node]
    tok = len(prompt) // 4

    print(f"\n  {n} documents · {len(prompt):,} chars · ~{tok:,} tokens")
    if not has_jasper():
        print(f"\n  🔴 THE JASPER BUNDLE (09_) IS NOT IN THE RECORD.")
        print(f"     Five of the seven requests concern the transfer, and this review would be")
        print(f"     answered without the documents that bear on it. Build the EXPANDED record:")
        print(f"       py -3.14 wargame_feed.py --build --expanded")
        print(f"     Nothing was called.\n")
        return 4
    print(f"  {node.upper()} / {model} · context {ctx:,}")

    if tok + 8000 > ctx and not no_fit:
        print(f"\n  ~{tok:,} tok will not fit {model}'s {ctx:,} window. Dropping one document:")
        for n, why in FIT_DROP.items():
            print(f"    - {n[:72]}\n        {why}")
        rec, n = load_record(drop=set(FIT_DROP))
        prompt = TASKING.read_text(encoding="utf-8") + rec
        tok = len(prompt) // 4
        print(f"  now {n} documents · {len(prompt):,} chars · ~{tok:,} tokens")

    if tok + 8000 > ctx:
        print(f"\n  🔴 REFUSING: ~{tok:,} tok exceeds {model}'s {ctx:,} window.")
        print(f"     Use a 1M rail: --node g43 or --node gem. Nothing was called.")
        print(f"     Do NOT solve this with a per-document cap - it would truncate the SOP")
        print(f"     file and the production PDF, which are what requests 27 and 30 turn on.\n")
        return 5
    print(f"  headroom {ctx - tok:,} tokens — OK")
    print(f"  (chars/4 measures ~12% HIGH, so the real count is lower still)\n")

    import mesh_fanout
    t0 = time.time()
    try:
        txt, meta = mesh_fanout.NODES[node](prompt)
    except Exception as e:
        secs = time.time() - t0
        OUT.mkdir(parents=True, exist_ok=True)
        (OUT / "returns").mkdir(exist_ok=True)
        (OUT / "returns" / f"RFA_REVIEW_{node}.FAILED.txt").write_text(
            f"node={node}\nmodel={model}\nsecs={secs:.1f}\nprompt_chars={len(prompt)}\n"
            f"exception={type(e).__name__}: {e}\n", encoding="utf-8")
        print(f"  🔴 CALL FAILED: {type(e).__name__}: {e}")
        return 3
    secs, usd = time.time() - t0, float(meta.get("cost_usd") or 0.0)

    dest = OUT / "returns" / f"RFA_REVIEW_{node}.md"
    dest.parent.mkdir(parents=True, exist_ok=True)
    n2 = 2
    while dest.exists():                                # never overwrite a paid return
        dest = OUT / "returns" / f"RFA_REVIEW_{node}_r{n2}.md"; n2 += 1
    if txt.strip():
        dest.write_text(txt, encoding="utf-8")
    else:
        dest.with_suffix(".FAILED.txt").write_text(f"meta={meta}\n", encoding="utf-8")
        print(f"  🔴 EMPTY RETURN")

    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    with LEDGER.open("a", encoding="utf-8") as f:
        f.write(json.dumps({"t": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "label": f"RFA-REVIEW-{node}", "node": node, "model": model,
                            "secs": round(secs, 1), "in_tok_est": tok, "chars": len(txt),
                            "usd": usd, "ok": bool(txt.strip())}) + "\n")

    print(f"  {'OK ' if txt.strip() else '🔴 '} {secs:6.1f}s  {len(txt):>8,} chars  ${usd:.4f}")
    print(f"  -> {dest}\n")
    print(f"  READ SECTION 3 FIRST - what is MISSING. A blind spot does not announce itself,")
    print(f"  which is why it has to come from somewhere other than the drafter.\n")
    return 0


def selftest() -> int:
    t = TASKING.read_text(encoding="utf-8") if TASKING.exists() else ""
    assert TASKING.exists(), f"tasking file missing at {TASKING}"
    for n in range(24, 31):
        assert f"  {n}. Admit" in t, f"proposed request {n} missing from the tasking"
    assert "A review that approves everything is useless" in t, "the anti-sycophancy line is gone"
    assert "DO NOT INVENT CASE LAW" in t, "the fabrication guard is gone"
    assert "WHAT IS MISSING" in t and "WHAT THE DRAFTER GOT WRONG" in t
    assert BUNDLE.match("09_JASPER_UCC__x.txt"), "the Jasper bundle must pass the whitelist"
    assert not BUNDLE.match("00_INDEX.txt")
    assert "gw" not in CTX, "grok-build's 256K cannot hold this record - do not offer it"
    # The fit-drop must never touch a document a request turns on.
    for keep in ("SOP", "PRODUCTION DOCS", "09_JASPER", "02_DISCOVERY"):
        assert not any(keep in n for n in FIT_DROP), f"FIT_DROP must never drop {keep}"
    assert len(FIT_DROP) == 1, "one named drop, not a growing list - a cap by another name"
    print("  selftest: tasking present, all 7 requests listed, anti-sycophancy and anti-fabrication")
    print("            guards intact, Jasper bundle passes the whitelist - PASS")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--node", default="sgh", choices=list(CTX))
    ap.add_argument("--no-fit", action="store_true",
                    help="never drop a document; refuse instead if it will not fit")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    return selftest() if a.selftest else fire(a.node, a.no_fit)


if __name__ == "__main__":
    sys.exit(main())
