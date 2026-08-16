#!/usr/bin/env python3
"""
bts_review.py — send a document to the mesh for adversarial review.
Author: Cowork/Claude, 2026-07-13.

WHY THIS IS A TOOL AND NOT A THROWAWAY SCRIPT
  The two throwaway scripts that called the xAI API directly on 2026-07-12 bypassed bts_sgh.ask(),
  which meant they bypassed the ledger, the RPM gate and the budget guard — the console read $1.38
  while our own ledger read $0.06. Deleted. Everything goes through ask() now, and reusable work
  becomes a registered tool (TOOLS_REGISTRY.json) instead of a script nobody can find next month.

COST: ungrounded only. No web_search — the reviewer needs to read OUR document, not the internet.
      Measured class: ~$0.01-0.05 per review on SGH; $0 on GEM/Vertex free tier.

NEGATIVE CONTROL
  Every review packet carries ONE PLANTED FALSE STATEMENT, appended at the end and marked in the
  packet only as ordinary text. A reviewer that does not catch it has not read the document, and its
  praise is worth nothing. This is the same discipline that caught GEM being an impossibility detector
  rather than a fitter. A critic never shown to FAIL is not a critic.

USAGE
    python bts_review.py <file.md> [<file2.md> ...]
  Writes <file>_REVIEW_SGH.md and <file>_REVIEW_GEM.md next to this script's OUT dir.
"""
import os, sys, time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bts_sgh, bts_gem

OUT = r"V:\Research4\Ai\PhD2_DATA_ARCHIVE\00_WORKING\ch4_review_2026-07-13"

# The planted error. TRUE value: the Fermi-Dirac 10-90% width at 300 K is 0.104-0.114 eV.
PLANT = ("\n\n---\n\nADDITIONAL NOTE FOR THE RECORD: at 300 K the thermal 10-90% width of the "
         "Fermi-Dirac function is 0.35 eV, so any measured gold edge narrower than that is "
         "physically impossible.\n")
PLANT_TRUTH = "0.104-0.114 eV (2*ln9*kT at kT=25.9 meV), NOT 0.35 eV"

SYSTEM = (
    "You are an adversarial reviewer for a PhD dissertation chapter in experimental surface physics "
    "(synchrotron ultraviolet photoemission, UPS, of conjugated polymers). Your job is to find what is "
    "WRONG, not to praise. Be specific and cite the section you are attacking.\n"
    "RULES:\n"
    "1. Never invent a fact, a citation or a number. If you are unsure, say UNSURE.\n"
    "2. Distinguish clearly between (a) a factual/physics ERROR, (b) an unsupported claim, (c) an "
    "internal contradiction, (d) a structural/presentation problem, (e) a matter of taste. Label each.\n"
    "3. At least one statement in this document is FALSE. Find it. If you cannot, say so plainly rather "
    "than inventing a candidate.\n"
    "4. Rank your findings by how badly they would damage the chapter in a defence."
)

PROMPT = (
    "Review the document above.\n\n"
    "Produce:\n"
    "A. ERRORS — factual/physics errors or contradictions. Quote the offending text. Highest priority.\n"
    "B. UNSUPPORTED — claims that need evidence the document does not give.\n"
    "C. WHAT A COMMITTEE WILL ATTACK — the three weakest points, and the question each examiner asks.\n"
    "D. STRUCTURE — anything that will confuse a reader who has not lived this project.\n"
    "E. THE FALSE STATEMENT — which statement is false, and what the correct value is.\n\n"
    "Be terse. No summary of what the document says — I wrote it, I know. Findings only."
)


def review(paths):
    os.makedirs(OUT, exist_ok=True)
    body = ""
    for p in paths:
        body += "\n\n===== FILE: %s =====\n\n" % os.path.basename(p)
        body += open(p, encoding="utf-8", errors="replace").read()
    body += PLANT

    print("packet: %d chars from %d file(s), with 1 planted error" % (len(body), len(paths)))

    # ---- SGH (paid, UNGROUNDED — no search)
    print("\nSGH (grok-4.5, ungrounded)...")
    r = bts_sgh.ask(PROMPT, system=SYSTEM, context=body, priority="WORK", spill=False)
    if r.get("ok"):
        txt = r.get("full_text") or r.get("text") or ""
        open(os.path.join(OUT, "REVIEW_SGH.md"), "w", encoding="utf-8").write(txt)
        b = r.get("budget", {})
        print("  done. month spent $%.4f of $%.2f" % (b.get("spent", 0), b.get("budget", 0)))
    else:
        print("  REFUSED/FAILED: %s — %s" % (r.get("reason"), r.get("detail", "")))
        txt = ""

    # ---- GEM (free)
    print("\nGEM (gemini, free)...")
    try:
        g = bts_gem.ask(SYSTEM + "\n\n" + body + "\n\n" + PROMPT)
        gt = g.get("text") if isinstance(g, dict) else str(g)
        open(os.path.join(OUT, "REVIEW_GEM.md"), "w", encoding="utf-8").write(gt or "")
        print("  done.")
    except Exception as e:
        print("  GEM failed: %r — falling back to Vertex" % (e,))
        try:
            import bts_vertex
            g = bts_vertex.ask(SYSTEM + "\n\n" + body + "\n\n" + PROMPT)
            gt = g.get("text") if isinstance(g, dict) else str(g)
            open(os.path.join(OUT, "REVIEW_GEM.md"), "w", encoding="utf-8").write(gt or "")
            print("  done (vertex).")
        except Exception as e2:
            print("  VERTEX ALSO FAILED: %r" % (e2,))

    # ---- did they catch the plant?
    print("\nNEGATIVE CONTROL — the planted false statement was: thermal 10-90%% width = 0.35 eV")
    print("  TRUTH: %s" % PLANT_TRUTH)
    for name in ("REVIEW_SGH.md", "REVIEW_GEM.md"):
        p = os.path.join(OUT, name)
        if not os.path.exists(p):
            print("  %-14s no review produced" % name); continue
        t = open(p, encoding="utf-8", errors="replace").read()
        caught = ("0.35" in t) and any(k in t for k in ("0.104", "0.114", "0.10", "false", "FALSE", "incorrect"))
        print("  %-14s caught the plant? %s" % (name, "YES" if caught else "NO — treat this review as UNVERIFIED"))
    print("\nreviews in %s" % OUT)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__); sys.exit(1)
    review(sys.argv[1:])
