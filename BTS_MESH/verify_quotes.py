"""Check every node-attributed QUOTATION in the docs against what the node actually wrote.

WHY THIS EXISTS
    2026-07-28: Keith noticed the word "vanity" in two supposedly independent node reviews. It was
    my word — I had put it in the prompt — and pulling the thread found worse: one of the two
    quotations attributed to GEM **appears nowhere in GEM's output**. I had paraphrased its
    position into my own vocabulary and set it in quotation marks, then written the pair up as a
    consensus in the handoff. The nodes had in fact DISAGREED.

    That is the same fabrication class this project has caught twice in outside nodes. Catching it
    in myself required Keith to spot a stylistic tell, which is not a control — it is luck.

WHAT IT DOES
    Extracts every `**NODE:** "..."` quotation from the docs, and greps the node's own output
    files for the string (whitespace- and markup-normalised). Prints VERBATIM or NOT FOUND.

    It cannot prove a quote is in context or fairly excerpted. It proves only that the words exist
    in what the node wrote — which is the minimum that quotation marks assert, and the thing that
    was false.

Run it before any handoff that quotes a node. Exit code 1 if anything fails to verify.
"""
from __future__ import annotations

import glob
import os
import re
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))

#: Where each node's raw returns live. Add to these when a new rail starts writing transcripts.
NODE_SOURCES: dict[str, tuple[str, ...]] = {
    "SGH": ("Ai/upsjudge/forge/rounds/*SGH*.md", "Ai/upsjudge/forge/review_b*_SGH.md",
            "Ai/PhD2_DATA_ARCHIVE/00_WORKING/*SGH*.md"),
    "GEM": ("Ai/upsjudge/forge/rounds/*GEM*.md", "Ai/upsjudge/forge/review_b*_GEM.md",
            "Ai/PhD2_DATA_ARCHIVE/00_WORKING/*GEM*.md"),
    "GW":  ("Ai/upsjudge/forge/rounds/*GW*.md", "Ai/upsjudge/forge/review_b*_GW.md"),
}

#: Documents that quote nodes and are read as authoritative.
DOC_GLOBS = ("BU.MD", "Ai/upsjudge/forge/rounds/*.md", "Ai/upsjudge/*.md", "Ai/*.md")

# The quotation must open IMMEDIATELY after the node label — at most a few characters of
# punctuation between. The first version allowed anything in between, which made it grab the next
# quoted string anywhere in the paragraph and report three false alarms on its first run:
#   * a phrase the surrounding text explicitly says "I wrote", not the node;
#   * a rule from the prompt TEMPLATE that happened to sit below an "**SGH:**" heading.
# A checker that cries wolf gets ignored, and then it is worse than no checker.
#: Two shapes are used across this project's docs, and BOTH must be caught:
#:    **SGH:** "quoted text"                    — prose
#:    | **SGH** | *"quoted text"* |             — comparison tables
#: The quotation must open IMMEDIATELY after the label, allowing only markup and table pipes
#: between. An earlier version allowed ANY intervening text and reported three false alarms on its
#: first run — a phrase the surrounding prose explicitly says "I wrote", and a rule from the prompt
#: TEMPLATE that merely sat below an "**SGH:**" heading. Tightening it then dropped five REAL
#: quotations, which is the opposite failure. A checker that cries wolf gets ignored; one that
#: finds nothing is decoration. It has to be exercised against a known fabrication — see
#: `--selftest`, which is the negative control this file is required to pass.
QUOTE_RE = re.compile(r'\*\*(SGH|GEM|GW|GBW)\**[:\s]*\**[\s>|*_]{0,8}["“]([^"”]{25,900})["”]')


def norm(s: str) -> str:
    """Whitespace- and markup-insensitive, so formatting differences do not read as fabrication."""
    s = re.sub(r"[`*_>]", "", s)
    s = s.replace("…", "").replace("—", "-").replace("–", "-")
    return re.sub(r"\s+", " ", s).strip().lower()


def corpus_for(node: str) -> str:
    out = []
    for pat in NODE_SOURCES.get(node, ()):
        for f in glob.glob(os.path.join(ROOT, pat)):
            try:
                with open(f, encoding="utf-8", errors="replace") as fh:
                    out.append(fh.read())
            except OSError:
                pass
    return norm("\n".join(out))


def selftest() -> int:
    """NEGATIVE CONTROL: prove the checker can FAIL, on the fabrication that motivated it.

    The retracted GEM quotation — "Building a new full-stack fitting GUI is vanity…" — appears
    nowhere in GEM's output. If this checker passes that string, it is not a checker.
    """
    hay = corpus_for("GEM")
    fabricated = "Building a new full-stack fitting GUI is vanity"
    genuine = "Build `upsjudge` as a headless library with a thin Qt GUI layer"
    ok_fab = norm(fabricated) not in hay
    ok_gen = norm(genuine) in hay
    print(f"  fabricated quote correctly NOT FOUND : {'PASS' if ok_fab else 'FAIL'}")
    print(f"  genuine quote correctly found        : {'PASS' if ok_gen else 'FAIL'}")
    if not (ok_fab and ok_gen):
        print("  SELFTEST FAILED — this tool cannot be trusted to detect a fabrication.")
        return 1
    print("  selftest OK: the checker discriminates.")
    return 0


def main() -> int:
    if "--selftest" in sys.argv:
        return selftest()
    corpora = {n: corpus_for(n) for n in NODE_SOURCES}
    bad = 0
    total = 0
    for pat in DOC_GLOBS:
        for doc in sorted(glob.glob(os.path.join(ROOT, pat))):
            try:
                with open(doc, encoding="utf-8", errors="replace") as fh:
                    text = fh.read()
            except OSError:
                continue
            for m in QUOTE_RE.finditer(text):
                node, quote = m.group(1), m.group(2)
                total += 1
                hay = corpora.get(node, "")
                if not hay:
                    print(f"?  {node:4} NO SOURCE FILES — cannot verify: {quote[:70]}")
                    continue
                # Check the quote in pieces: an ellipsis joins two separated passages, and each
                # side must appear even though the joined string never will.
                parts = [p for p in re.split(r"…|\.\.\.", quote) if len(norm(p)) > 20]
                missing = [p for p in (parts or [quote]) if norm(p) not in hay]
                if missing:
                    bad += 1
                    print(f"✗  {node:4} NOT FOUND in {os.path.relpath(doc, ROOT)}")
                    for p in missing:
                        print(f"        {norm(p)[:110]}")
                else:
                    print(f"✓  {node:4} verbatim  ({os.path.relpath(doc, ROOT)})")

    print(f"\n{total} quotation(s) checked · {bad} could not be verified")
    if bad:
        print("A quotation that is not verbatim is a FABRICATION. Fix the document, not this tool.")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
